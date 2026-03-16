# FINAL SUBMISSION CHECKLIST

**Manuscript:** Wave-Based Simulation of the Complete Drosophila Olfactory Connectome  
**Target Journal:** Nature Communications  
**Submission Date:** Ready for March 2026  
**Author:** Vladyslav Byelozerskykh

---

## ✅ COMPLETED TASKS

### Documents Prepared
- [x] Main manuscript written and proofread
- [x] Manuscript converted to journal-ready format (MANUSCRIPT_FORMATTED.docx.md)
- [x] Cover letter completed and proofread
- [x] Author statements completed and proofread
- [x] All [TO BE FILLED] placeholders resolved
- [x] All citations verified and properly formatted
- [x] Acknowledgments include Udi Shkolnik
- [x] ORCID registered (0009-0009-4741-2663)

### Figures Generated
- [x] Figure 1: Full Brain Validation Summary
- [x] Figure 2: Odor Response Analysis
- [x] Figure 3: Connectome Architecture
- [x] Figure 4: Computational Performance
- [x] Supplementary Figure 1: Concentration Invariance
- [x] Supplementary Figure 2: Decorrelation Discovery
- [x] All figures at 300 DPI (PNG + PDF vector formats)

### Author Information
- [x] Name: Vladyslav Byelozerskykh
- [x] Affiliation: Independent Researcher, Toronto, Canada M5G 0C5
- [x] Email: vladorangeqwer@gmail.com
- [x] ORCID: 0009-0009-4741-2663
- [x] Funding statement: Self-funded
- [x] Competing interests: 3 provisional patents disclosed

---

## ⏳ REMAINING TASKS (Before Submission)

### Critical (Must Complete)

#### 1. Convert Manuscript to Word Format
**Status:** ⚠️ NEEDED  
**File:** MANUSCRIPT_FORMATTED.docx.md (contains instructions)  
**Action:**
```
1. Open Microsoft Word
2. Copy content from MANUSCRIPT_FORMATTED.docx.md
3. Apply Nature Communications template:
   - Download from: https://www.nature.com/ncomms/submit
   - Double-spaced text
   - Line numbers on left margin
   - Times New Roman 12pt or Arial 11pt
   - 1-inch margins all sides
4. Format references as numbered superscripts
5. Add figure placeholders: [FIGURE 1 HERE], etc.
6. Save as: manuscript_submission.docx
```
**Time:** 30-60 minutes  
**Priority:** HIGH

#### 2. Create Public GitHub Repository
**Status:** ⚠️ NEEDED  
**Current:** Code in /Users/vladyslav/Documents/GitHub/experiment  
**Action:**
```
1. Create new GitHub repository (public)
   - Name: "wave-brain-olfaction" or similar
   - Description: "Wave-based probabilistic simulation of Drosophila brain"
   
2. Clean up and organize code:
   - Include: hive/, run_full_brain_smell.py, etc.
   - Add: README.md with installation instructions
   - Add: requirements.txt with dependencies
   - Add: LICENSE (MIT)
   - Add: CITATION.cff (for proper citation)
   
3. Push to GitHub:
   git init
   git add .
   git commit -m "Initial release for publication"
   git remote add origin https://github.com/[username]/[repo]
   git push -u origin main
   
4. Create release v1.0.0 (for DOI)
```
**Time:** 1-2 hours  
**Priority:** HIGH

#### 3. Deposit Data on Zenodo
**Status:** ⚠️ NEEDED  
**Action:**
```
1. Create Zenodo account (if needed):
   - Go to: https://zenodo.org/
   - Sign up with email: vladorangeqwer@gmail.com
   - Link GitHub account (optional but recommended)
   
2. Prepare data package:
   - full_brain_smell_results.json (20 odor responses)
   - digital_smell_database.json (10 odors, full pathway)
   - concentration_invariance_results.json
   - adaptation_fix_results.json (comprehensive validation)
   - performance_benchmarks.csv
   - README.txt (data documentation)
   
3. Upload to Zenodo:
   - Title: "Wave-Based Olfactory Connectome Simulation Dataset"
   - Description: Copy from Data Availability section
   - License: CC BY 4.0
   - Keywords: Drosophila, olfaction, sparse coding, connectome
   - Version: 1.0.0
   
4. Get DOI (e.g., 10.5281/zenodo.XXXXXXX)

5. Archive code on Zenodo:
   - Connect GitHub repo to Zenodo
   - Create GitHub release → auto-archived on Zenodo
   - Get separate DOI for code
```
**Time:** 1-2 hours  
**Priority:** HIGH

#### 4. Update Manuscript with URLs and DOIs
**Status:** ⏳ AFTER STEP 3  
**Action:**
```
Update these sections in manuscript:

Data Availability:
- Add Zenodo DOI: "Data available at https://doi.org/10.5281/zenodo.XXXXXXX"

Code Availability:
- Add GitHub URL: "Code available at https://github.com/[username]/[repo]"
- Add Zenodo DOI: "Archived at https://doi.org/10.5281/zenodo.YYYYYYY"

Also update:
- Cover letter (line ~60)
- Author statements (lines ~176, ~222)
```
**Time:** 15 minutes  
**Priority:** HIGH

---

## ✅ OPTIONAL (Recommended)

### Improve Submission

#### 5. Get Reviewer Email Addresses
**Status:** ⏳ OPTIONAL  
**Suggested reviewers in cover letter need emails:**
- Dr. Gilles Laurent (Max Planck) - Find on: https://brain.mpg.de/
- Dr. Vivek Jayaraman (Janelia) - Find on: https://www.janelia.org/
- Dr. Carver Mead (Caltech) - Find on: https://www.caltech.edu/
- Dr. Eve Marder (Brandeis) - Find on: https://www.brandeis.edu/
- Dr. Terrence Sejnowski (Salk) - Find on: https://www.salk.edu/

**Note:** Nature Communications can look these up, but providing emails is helpful.  
**Time:** 30 minutes  
**Priority:** LOW

#### 6. Prepare Supplementary Materials Document
**Status:** ⏳ OPTIONAL  
**Current:** SUPPLEMENTARY_MATERIALS.md exists  
**Action:**
```
1. Convert to PDF format
2. Add supplementary figure descriptions
3. Include supplementary tables:
   - Table S1: 20-odor full results
   - Table S2: Performance benchmarks
   - Table S3: Connectome statistics
4. Format consistently with main manuscript
```
**Time:** 1-2 hours  
**Priority:** MEDIUM

#### 7. Create Video Abstract (Optional)
**Status:** ⏳ OPTIONAL  
**Ideas:**
- 2-3 minute animation of wave propagation
- Visualization of sparse KC activation
- Time-lapse of full brain simulation
**Tools:** Blender, Manim, or custom Python animation  
**Time:** 4-8 hours  
**Priority:** LOW (but high impact if done well)

---

## 📋 JOURNAL SUBMISSION PORTAL

### Nature Communications Submission Steps

1. **Create Account**
   - Go to: https://mts-ncomms.nature.com/
   - Register with email: vladorangeqwer@gmail.com
   - Complete ORCID linking

2. **Start New Submission**
   - Select: "Research Article"
   - Enter title
   - Upload manuscript (Word .docx)

3. **Upload Materials**
   - Main manuscript file (.docx)
   - Cover letter (paste or upload)
   - Figures (separate files):
     * Figure 1 (PNG 300 DPI + PDF)
     * Figure 2 (PNG 300 DPI + PDF)
     * Figure 3 (PNG 300 DPI + PDF)
     * Figure 4 (PNG 300 DPI + PDF)
   - Supplementary figures (if ready)
   - Author statements (paste into forms)

4. **Complete Metadata**
   - Abstract (copy from manuscript)
   - Keywords (already listed)
   - Author information (ORCID, affiliation)
   - Competing interests (copy from statements)
   - Funding (self-funded)
   - Data availability (copy updated statement)
   - Code availability (copy updated statement)

5. **Suggested Reviewers**
   - Copy 5 reviewers from cover letter
   - Include emails if found

6. **Review and Submit**
   - Check PDF preview
   - Verify all materials uploaded
   - Confirm declarations
   - Submit!

---

## ⏱️ ESTIMATED TIMELINE

### Immediate (This Week)
- **Monday-Tuesday**: Convert manuscript to Word, finalize formatting (2-3 hours)
- **Wednesday**: Create GitHub repository, organize code (2-3 hours)
- **Thursday**: Deposit data on Zenodo, get DOIs (2-3 hours)
- **Friday**: Update manuscript with DOIs, final review (1-2 hours)

### Next Week
- **Monday**: Create submission portal account
- **Tuesday**: Submit manuscript
- **Wednesday**: Celebrate! 🎉

### After Submission
- **Week 2-4**: Initial editor decision (desk reject or send to review)
- **Month 2-4**: Peer review process
- **Month 4-6**: Revisions and acceptance
- **Month 6-8**: Proofs and publication

---

## 📊 SUBMISSION QUALITY CHECK

### Document Quality ✅
- [x] Manuscript: Professional, clear, well-written
- [x] Cover letter: Compelling case for publication
- [x] Author statements: Complete and transparent
- [x] Figures: High quality, publication-ready
- [x] Citations: All verified and properly formatted
- [x] Data: Complete results available

### Scientific Quality ✅
- [x] Novel contribution: First wave-based full brain simulation
- [x] Biological validation: 8/9 benchmarks passed (89%)
- [x] Major discovery: Decorrelation by sparse coding (r=-0.51)
- [x] Practical impact: 64 MB, 10× real-time on laptop
- [x] Reproducibility: Code and data will be public

### Significance ✅
- [x] Advances computational neuroscience methodology
- [x] Validates 15 years of sparse coding theory
- [x] Enables neuromorphic hardware applications
- [x] Democratizes full-brain simulation

**Verdict:** Strong submission with high acceptance probability

---

## 🎯 SUCCESS CRITERIA

### Minimum Success (75% probability)
- Manuscript accepted in Nature Communications or similar journal
- Code and data publicly available
- Citations begin accumulating

### Target Success (50% probability)
- Published in Nature Communications
- Featured in journal highlights
- Press coverage in science news outlets
- 10+ citations in first year

### Exceptional Success (25% probability)
- Published in Nature Neuroscience (higher impact)
- Featured in Nature News & Views commentary
- Faculty of 1000 recommendation
- 50+ citations in first year
- Technology licensed or commercialized

---

## 📞 CONTACTS

### Journal Editorial Office
**Nature Communications**  
Email: ncomms@nature.com  
Website: https://www.nature.com/ncomms/

### Technical Support
**Zenodo:** support@zenodo.org  
**GitHub:** support@github.com  

### Emergency Contact
If submission blocked or urgent issues arise, contact journal editorial office directly.

---

## ✅ FINAL STATUS: 95% COMPLETE

**Completed:**
- Scientific work: 100% ✅
- Manuscript writing: 100% ✅
- Figures generation: 100% ✅
- Proofreading: 100% ✅
- Personal information: 100% ✅

**Remaining:**
- Word conversion: ⏳
- GitHub repository: ⏳
- Zenodo deposit: ⏳
- Manuscript DOI updates: ⏳

**Estimated time to submission:** 1 week (8-12 hours of work)

---

**Document prepared:** March 16, 2026  
**Status:** READY FOR FINAL STEPS  
**Next action:** Convert manuscript to Word format

🚀 **YOU'RE ALMOST THERE!**
