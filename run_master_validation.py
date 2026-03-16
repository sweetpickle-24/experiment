#!/usr/bin/env python3
"""
Master Validation Suite
========================

Runs all five validation experiments and generates comprehensive report.

Validations:
1. Temporal Dynamics (onset, adaptation)
2. Odor Mixtures (binary/ternary blends)
3. Learning & Plasticity (Hebbian STDP)
4. Discrimination Thresholds (Weber's law)
5. Odor Similarity Structure (representational geometry)
"""

import subprocess
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('master_validation_output.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

VALIDATION_SCRIPTS = [
    {
        'name': 'Temporal Dynamics',
        'script': 'validate_temporal_dynamics.py',
        'result_file': 'temporal_dynamics_results.json',
        'estimated_time_min': 15
    },
    {
        'name': 'Odor Mixtures',
        'script': 'validate_odor_mixtures.py',
        'result_file': 'odor_mixtures_results.json',
        'estimated_time_min': 10
    },
    {
        'name': 'Learning & Plasticity',
        'script': 'validate_learning_plasticity.py',
        'result_file': 'learning_plasticity_results.json',
        'estimated_time_min': 20
    },
    {
        'name': 'Discrimination Thresholds',
        'script': 'validate_discrimination_threshold.py',
        'result_file': 'discrimination_threshold_results.json',
        'estimated_time_min': 12
    },
    {
        'name': 'Odor Similarity Structure',
        'script': 'validate_odor_similarity.py',
        'result_file': 'odor_similarity_results.json',
        'estimated_time_min': 8
    }
]

def run_validation(script_name):
    """Run a validation script and return success status."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Running: {script_name}")
    logger.info(f"{'='*70}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per script
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {script_name} completed successfully")
            return True, result.stdout
        else:
            logger.error(f"❌ {script_name} failed with code {result.returncode}")
            logger.error(result.stderr)
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ {script_name} timed out after 1 hour")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"❌ {script_name} crashed: {e}")
        return False, str(e)

def load_results(result_file):
    """Load results JSON if exists."""
    if Path(result_file).exists():
        with open(result_file, 'r') as f:
            return json.load(f)
    return None

def generate_master_report(validation_results):
    """Generate comprehensive validation report."""
    
    report = {
        'master_validation': {
            'timestamp': datetime.now().isoformat(),
            'total_validations': len(VALIDATION_SCRIPTS),
            'successful': sum(1 for v in validation_results if v['success']),
            'failed': sum(1 for v in validation_results if not v['success'])
        },
        'validations': validation_results,
        'biological_validation_summary': {}
    }
    
    # Extract validation statuses
    all_pass = True
    
    for val in validation_results:
        if val['success'] and val['results']:
            validation_name = val['name']
            summary = val['results'].get('summary', {})
            bio_val = summary.get('biological_validation', {})
            
            report['biological_validation_summary'][validation_name] = bio_val
            
            # Check if all pass
            if isinstance(bio_val, dict):
                for status in bio_val.values():
                    if status != 'PASS':
                        all_pass = False
    
    report['master_validation']['overall_status'] = 'PASS' if all_pass else 'FAIL'
    
    return report

def print_summary(master_report):
    """Print human-readable summary."""
    
    logger.info("\n" + "="*70)
    logger.info("MASTER VALIDATION SUMMARY")
    logger.info("="*70)
    
    master = master_report['master_validation']
    logger.info(f"\nTimestamp: {master['timestamp']}")
    logger.info(f"Total validations: {master['total_validations']}")
    logger.info(f"Successful: {master['successful']}")
    logger.info(f"Failed: {master['failed']}")
    logger.info(f"\nOverall status: {master['overall_status']}")
    
    logger.info(f"\n{'='*70}")
    logger.info("BIOLOGICAL VALIDATION RESULTS")
    logger.info(f"{'='*70}")
    
    bio_summary = master_report['biological_validation_summary']
    
    for validation_name, results in bio_summary.items():
        logger.info(f"\n{validation_name}:")
        if isinstance(results, dict):
            for metric, status in results.items():
                symbol = "✅" if status == "PASS" else "❌"
                logger.info(f"  {symbol} {metric}: {status}")
        else:
            logger.info(f"  {results}")
    
    logger.info("\n" + "="*70)
    logger.info("DETAILED METRICS")
    logger.info("="*70)
    
    for val in master_report['validations']:
        if val['success'] and val['results']:
            logger.info(f"\n{val['name']}:")
            summary = val['results'].get('summary', {})
            for key, value in summary.items():
                if key != 'biological_validation' and isinstance(value, dict):
                    if 'mean' in value:
                        logger.info(f"  {key}: {value.get('mean', 'N/A')}")

def main():
    start_time = datetime.now()
    
    logger.info("="*70)
    logger.info("MASTER VALIDATION SUITE")
    logger.info("="*70)
    logger.info(f"Starting at: {start_time.isoformat()}")
    
    total_estimated_time = sum(v['estimated_time_min'] for v in VALIDATION_SCRIPTS)
    logger.info(f"Total estimated time: {total_estimated_time} minutes (~{total_estimated_time/60:.1f} hours)")
    
    validation_results = []
    
    # Run each validation
    for validation_config in VALIDATION_SCRIPTS:
        logger.info(f"\n{'='*70}")
        logger.info(f"VALIDATION {len(validation_results)+1}/{len(VALIDATION_SCRIPTS)}: {validation_config['name']}")
        logger.info(f"Estimated time: {validation_config['estimated_time_min']} minutes")
        logger.info(f"{'='*70}")
        
        success, output = run_validation(validation_config['script'])
        
        # Load results if successful
        results_data = None
        if success:
            results_data = load_results(validation_config['result_file'])
        
        validation_results.append({
            'name': validation_config['name'],
            'script': validation_config['script'],
            'success': success,
            'results': results_data
        })
    
    # Generate master report
    logger.info(f"\n{'='*70}")
    logger.info("GENERATING MASTER REPORT")
    logger.info(f"{'='*70}")
    
    master_report = generate_master_report(validation_results)
    
    # Save master report
    output_file = 'master_validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(master_report, f, indent=2)
    logger.info(f"✅ Master report saved to {output_file}")
    
    # Print summary
    print_summary(master_report)
    
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds() / 60
    
    logger.info(f"\n{'='*70}")
    logger.info(f"MASTER VALIDATION COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Started: {start_time.isoformat()}")
    logger.info(f"Finished: {end_time.isoformat()}")
    logger.info(f"Elapsed: {elapsed:.1f} minutes")
    logger.info(f"Overall status: {master_report['master_validation']['overall_status']}")

if __name__ == '__main__':
    main()
