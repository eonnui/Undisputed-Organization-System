from pypdf import PdfReader

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_file: str) -> list:
    try:
        with open(pdf_file, 'rb') as pdf:
            reader = PdfReader(pdf, strict=False)
            pdf_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pdf_text.append(text)
            return pdf_text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []

def extract_student_info(extracted_text: list) -> dict:
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
        student['campus'] = entries[0] if len(entries) > 0 else None

        if len(entries) > 1:
            words = entries[1].split(' ')
            if len(words) >= 3:
                student['student_number'] = words[0]
                student['semester'] = words[1]
                student['school_year'] = words[2]
            else:
                student['student_number'] = None
                student['semester'] = None
                student['school_year'] = None
        else:
            student['student_number'] = None
            student['semester'] = None
            student['school_year'] = None

        if len(entries) > 2:
            words = entries[2].split(' ')
            name_parts = []
            for word in words:
                word = word.replace(',', '')
                if word.upper() in {'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'}:
                    break
                name_parts.append(word)
            name = ' '.join(name_parts)
            student['name'] = name if name_parts else None
        else:
            student['name'] = None

        if len(entries) > 3:
            student_info = entries[3].split(' ')
            if len(student_info) >= 2:
                student['course'] = student_info[0]
                student['year_level'] = student_info[1]
            else:
                student['course'] = None
                student['year_level'] = None
        else:
            student['course'] = None
            student['year_level'] = None

        if len(entries) > 4:
            section_parts = entries[4].split(' ')
            if len(section_parts) >= 1:
                student['section'] = section_parts[-1]
                student['address'] = ' '.join(section_parts[:-1])
            else:
                student['section'] = None
                student['address'] = None
        else:
            student['section'] = None
            student['address'] = None

    return student
