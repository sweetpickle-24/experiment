#!/usr/bin/env python3
"""
Convert manuscript from Markdown to Word format using python-docx
"""

try:
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("python-docx not installed. Installing...")
    import subprocess
    subprocess.run(["pip3", "install", "python-docx"], check=True)
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

import re

def create_word_manuscript():
    """Create Word document from manuscript"""
    
    # Read the markdown manuscript
    with open('MANUSCRIPT_PUBLICATION.md', 'r') as f:
        content = f.read()
    
    # Create Word document
    doc = Document()
    
    # Set default font and spacing
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    paragraph_format = style.paragraph_format
    paragraph_format.line_spacing = 2.0  # Double spacing
    paragraph_format.space_after = Pt(0)
    
    # Split content into lines
    lines = content.split('\n')
    
    # Track current section
    in_code_block = False
    skip_until_intro = True
    
    for i, line in enumerate(lines):
        # Skip YAML front matter and initial markdown headers until we get to content
        if line.startswith('---') and i < 20:
            continue
        if line.startswith('#') and 'Wave-Based Simulation' in line:
            skip_until_intro = False
            
            # Title
            title = doc.add_paragraph()
            title_run = title.add_run(line.replace('#', '').strip())
            title_run.bold = True
            title_run.font.size = Pt(16)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            continue
            
        if skip_until_intro:
            continue
            
        # Handle different markdown elements
        if line.startswith('```'):
            in_code_block = not in_code_block
            continue
            
        if in_code_block:
            # Code blocks with smaller font
            p = doc.add_paragraph(line)
            p.style = 'No Spacing'
            for run in p.runs:
                run.font.name = 'Courier New'
                run.font.size = Pt(10)
            continue
            
        # Headers
        if line.startswith('## '):
            p = doc.add_paragraph()
            run = p.add_run(line.replace('##', '').strip())
            run.bold = True
            run.font.size = Pt(14)
            run.font.all_caps = True
            continue
        elif line.startswith('### '):
            p = doc.add_paragraph()
            run = p.add_run(line.replace('###', '').strip())
            run.bold = True
            run.font.size = Pt(13)
            continue
        elif line.startswith('#### '):
            p = doc.add_paragraph()
            run = p.add_run(line.replace('####', '').strip())
            run.bold = True
            run.italic = True
            run.font.size = Pt(12)
            continue
            
        # Tables (simple handling)
        if line.startswith('|') and '|' in line[1:]:
            # Just add as regular text for now (can be formatted manually)
            p = doc.add_paragraph(line)
            p.style = 'No Spacing'
            for run in p.runs:
                run.font.size = Pt(11)
            continue
            
        # Empty lines
        if not line.strip():
            doc.add_paragraph()
            continue
            
        # Bold/italic handling
        p = doc.add_paragraph()
        
        # Split by bold markers
        parts = re.split(r'(\*\*[^*]+\*\*)', line)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                run = p.add_run(part[2:-2])
                run.bold = True
            else:
                # Check for italic
                italic_parts = re.split(r'(\*[^*]+\*)', part)
                for ipart in italic_parts:
                    if ipart.startswith('*') and ipart.endswith('*') and not ipart.startswith('**'):
                        run = p.add_run(ipart[1:-1])
                        run.italic = True
                    else:
                        # Clean up reference citations
                        ipart = re.sub(r'\(([A-Z][a-z]+ (?:et al\.|& [A-Z][a-z]+), \d{4})\)', r'(\1)', ipart)
                        p.add_run(ipart)
    
    # Save document
    output_file = 'manuscript_submission.docx'
    doc.save(output_file)
    print(f"\n✓ Created: {output_file}")
    print(f"\nNext steps:")
    print(f"1. Open {output_file} in Microsoft Word")
    print(f"2. Apply Nature Communications template if needed")
    print(f"3. Add line numbers: Layout → Line Numbers → Continuous")
    print(f"4. Insert figures as placeholders: [FIGURE 1 HERE], etc.")
    print(f"5. Review and save")
    
    return output_file

if __name__ == '__main__':
    create_word_manuscript()
