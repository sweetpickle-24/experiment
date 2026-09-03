"""
Odorant name resolution in the DoOR client.

These tests exist because the lookup used to return a zero vector for any name
it did not recognise, print a warning, and let the caller continue. A zero
pattern correlates with itself at exactly 1.0 at every concentration, so an
unrecognised odorant raised the reported concentration-invariance mean instead
of failing the run.

Index and receptor-count expectations below were read off
data/door_consensus_matrix.npy directly.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hive.data.door_client import (  # noqa: E402
    DoorClient,
    OdorantNotFoundError,
    normalize_odorant_name,
)


# name -> (index in the matrix, number of nonzero receptors, max response)
VERIFIED_ODORANTS = {
    'benzaldehyde':      (136, 33, 0.655),
    '2-heptanone':       (63,  33, 0.364),
    'ethyl_acetate':     (200, 32, 0.492),
    'isopentyl_acetate': (267, 31, 0.438),
}


@pytest.fixture(scope='module')
def client():
    return DoorClient(data_dir=str(Path(__file__).resolve().parents[1] / 'data'))


@pytest.mark.parametrize('name', sorted(VERIFIED_ODORANTS))
def test_verified_odorant_resolves_to_nonzero_vector(client, name):
    idx, n_nonzero, max_response = VERIFIED_ODORANTS[name]

    assert client.resolve_odorant_name(name) == name
    assert client.odorant_names.index(name) == idx

    response = client.get_odorant_response(name)
    assert response.shape == (len(client.receptor_names),)
    assert np.count_nonzero(response) == n_nonzero
    assert response.max() == pytest.approx(max_response, abs=1e-3)

    # The specific defect: a zero vector passed as a valid response.
    assert np.any(response != 0)


def test_geosmin_raises(client):
    """geosmin is genuinely absent from the matrix, not a naming variant."""
    with pytest.raises(OdorantNotFoundError) as excinfo:
        client.get_odorant_response('geosmin')

    assert 'geosmin' in str(excinfo.value)
    assert excinfo.value.name == 'geosmin'


def test_spaced_name_resolves(client):
    """'ethyl acetate' with a space is the same molecule as 'ethyl_acetate'."""
    assert client.resolve_odorant_name('ethyl acetate') == 'ethyl_acetate'

    spaced = client.get_odorant_response('ethyl acetate')
    underscored = client.get_odorant_response('ethyl_acetate')
    assert np.array_equal(spaced, underscored)
    assert np.any(spaced != 0)


def test_isoamyl_acetate_resolves_to_isopentyl_acetate(client):
    """Isoamyl and isopentyl acetate are both 3-methylbutyl acetate."""
    for variant in ('isoamyl acetate', 'isoamyl_acetate', '3-methylbutyl_acetate'):
        assert client.resolve_odorant_name(variant) == 'isopentyl_acetate'

    response = client.get_odorant_response('isoamyl acetate')
    assert np.array_equal(response, client.get_odorant_response('isopentyl_acetate'))
    assert np.any(response != 0)


def test_miss_reports_close_matches(client):
    """A near-miss should name the candidates rather than just failing."""
    with pytest.raises(OdorantNotFoundError) as excinfo:
        client.get_odorant_response('benzaldehide')

    assert 'benzaldehyde' in excinfo.value.candidates


def test_case_and_whitespace_are_normalised(client):
    assert client.resolve_odorant_name('  Ethyl   Acetate  ') == 'ethyl_acetate'
    assert client.resolve_odorant_name('BENZALDEHYDE') == 'benzaldehyde'


def test_glomerular_pattern_path_also_raises(client):
    """The projection path must not bypass name resolution."""
    with pytest.raises(OdorantNotFoundError):
        client.get_glomerular_pattern('geosmin')


def test_normalize_is_usable_without_a_client():
    known = ['ethyl_acetate', 'isopentyl_acetate', '2-heptanone']
    assert normalize_odorant_name('ethyl acetate', known) == 'ethyl_acetate'
    assert normalize_odorant_name('isoamyl acetate', known) == 'isopentyl_acetate'
    with pytest.raises(OdorantNotFoundError):
        normalize_odorant_name('geosmin', known)


def test_missing_data_file_raises_instead_of_fabricating(tmp_path):
    """
    An absent matrix must not silently become a random one.

    The generator used to run on this path and save its output to the canonical
    filename, so a failed download left fabricated data in place permanently.
    """
    with pytest.raises(FileNotFoundError):
        DoorClient(data_dir=str(tmp_path / 'nonexistent'))


def test_synthetic_is_opt_in_and_not_written_to_disk(tmp_path):
    target = tmp_path / 'synthetic'
    client = DoorClient(data_dir=str(target), allow_synthetic=True)

    assert client.is_synthetic is True
    assert len(client.odorant_names) > 0
    assert not (target / 'door_consensus_matrix.npy').exists()
