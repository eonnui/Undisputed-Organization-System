from pypdf import PdfReader
from typing import List

def extract_text_from_pdf(pdf_file: str) -> List[str]:
    with open(pdf_file, 'rb') as pdf:
        reader = PdfReader(pdf, strict=False)
        pdf_text = []
        for page in reader.pages:
            pdf_text.append(page.extract_text())
        
        return extract_student_info(pdf_text)

def extract_student_info(extracted_text):
    entries = []
    limit = 5
    for page in extracted_text:
        page_entries = page.strip().split('\n')
        for entry in page_entries:
            if len(entries) < limit:
                entries.append(entry.strip())
            else:
                break
        if len(entries) >= limit:
            break

    student = {}
    if entries:
        student['campus'] = entries[0]
        if len(entries) > 1:
            words = entries[1].split(' ')
            if len(words) >= 3:
                student['student_number'] = words[0]
                student['semester'] = words[1]
                student['school_year'] = words[2]
        if len(entries) > 2:
            words = entries[2].split(' ')
            name_parts = []
            for word in words:
                word = word.replace(',', '')
                if word.upper() in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
                    break
                name_parts.append(word)
            name = ' '.join(name_parts)
            if name_parts:
                student['name'] = name
        if len(entries) > 3:
            student_info = entries[3].split(' ')
            if len(student_info) >= 2:
                student['course'] = student_info[0]
                student['year'] = student_info[1]
        if len(entries) > 4:
            section_parts = entries[4].split(' ')
            if len(section_parts) >= 4:
                add_section = len(section_parts)
                student['section'] = section_parts[add_section - 1]
                section_parts.remove(student['section'])
                student['address'] = ' '.join(section_parts)

        return student


if __name__ == '__main__':
    extracted_text = extract_text_from_pdf('sample2.pdf')
    print(extracted_text)



  