# text.py
from pypdf import PdfReader
from typing import List
import re  # Import the regular expression module
from datetime import datetime

def extract_text_from_pdf(pdf_file: str) -> List[str]:
    """
    Extracts text from a PDF file.

    Args:
        pdf_file (str): The path to the PDF file.

    Returns:
        List[str]: A list of strings, where each string represents the text
                     extracted from a page of the PDF.  Returns an empty list
                     if the PDF cannot be read or is empty.
    """
    try:
        with open(pdf_file, 'rb') as pdf:
            reader = PdfReader(pdf, strict=False)
            pdf_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:  # Only add if not None or empty
                    pdf_text.append(text)
            return pdf_text
    except Exception as e:
        print(f"Error reading PDF: {e}")  # Log the error
        return []  # Return an empty list on error

def extract_student_info(extracted_text: List[str]) -> dict:
    """
    Extracts student information from the text extracted from a PDF.  Handles
    potential errors in the structure of the extracted text.

    Args:
        extracted_text (List[str]): A list of strings, where each string
                                     represents text from a page of the PDF.

    Returns:
        dict: A dictionary containing the extracted student information.
              Returns an empty dictionary if no information could be extracted.
              Handles more robustly if entries are missing.
    """
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

        # Handle the case where entries[1] might not exist
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
                # Improved day matching using a set and direct comparison
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
                student['year_level'] = student_info[1]  # Changed 'year' to 'year_level' to match model
            else:
                student['course'] = None
                student['year_level'] = None
        else:
            student['course'] = None
            student['year_level'] = None

        if len(entries) > 4:
            section_parts = entries[4].split(' ')
            if len(section_parts) >= 1: # Changed from 4 to 1.  Addresses the index error
                student['section'] = section_parts[-1]
                student['address'] = ' '.join(section_parts[:-1])  # join all but the last element.
            else:
                student['section'] = None
                student['address'] = None
        else:
            student['section'] = None
            student['address'] = None

    return student

def is_valid_school_year(school_year: str) -> bool:
    """
    Validates the format of a school year string (e.g., "2024-2025").

    Args:
        school_year (str): The school year string to validate.

    Returns:
        bool: True if the school year is valid, False otherwise.
    """
    if not school_year:
        return False
    match = re.match(r"^(\d{4})-(\d{4})$", school_year)
    if not match:
        return False
    year1 = int(match.group(1))
    year2 = int(match.group(2))
    return year2 == year1 + 1

def is_within_valid_school_year(school_year: str) -> bool:
    """
    Checks if a given school year is the current or previous school year.

    Args:
        school_year (str): The school year string to check (e.g., "2024-2025").

    Returns:
        bool: True if the school year is current or previous, False otherwise.
    """
    if not is_valid_school_year(school_year):
        return False

    current_year = datetime.now().year
    # Extract the first year from the school year string
    year1 = int(school_year.split('-')[0])

    # Check if the school year is the current or previous
    return year1 == current_year or year1 == current_year - 1
if __name__ == '__main__':
    extracted_text = extract_text_from_pdf('sample2.pdf')  # corrected the filename
    if extracted_text:
        student_info = extract_student_info(extracted_text)
        print(student_info)
    else:
        print("Could not extract text from PDF.")

    #test the school year validation
    print(is_valid_school_year("2023-2024"))  # True
    print(is_valid_school_year("2023-2025"))  # False
    print(is_valid_school_year("2023"))        # False
    print(is_valid_school_year("abc-def"))     # False
    print(is_valid_school_year(None))          # False

    # Test the within valid school year function
    print(is_within_valid_school_year("2024-2025")) # True (if current year is 2024 or 2025)
    print(is_within_valid_school_year("2023-2024")) # True (if current year is 2024)
    print(is_within_valid_school_year("2022-2023")) # False (if current year is 2024)
    print(is_within_valid_school_year("2025-2026")) # False (if current year is 2024)
    print(is_within_valid_school_year(None))          # False
