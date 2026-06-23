import fitz  # PyMuPDF

def extract_text_from_pdfs(uploaded_files):
    full_text = ""
    file_names = []

    for uploaded_file in uploaded_files:
        file_names.append(uploaded_file.name)
        try:
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            full_text += f"\n\n===== شروع فایل: {uploaded_file.name} =====\n\n"

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text and text.strip():
                    full_text += f"\n--- صفحه {page_num} ---\n{text}\n"

            full_text += f"\n===== پایان فایل: {uploaded_file.name} =====\n\n"
            doc.close()

        except Exception as e:
            full_text += f"\n[خطا در خواندن فایل {uploaded_file.name}: {str(e)}]\n"

    return full_text.strip(), file_names
