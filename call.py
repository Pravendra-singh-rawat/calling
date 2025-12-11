import streamlit as st
import pandas as pd
from io import BytesIO
import tempfile
import os
import pytesseract
from PIL import Image
import fitz # PyMuPDF library is imported as fitz
import re # Added for robust text splitting

# --- Configure Tesseract Path (For local testing only) ---
# For deployment, the Tesseract path is handled by the Docker container's PATH variable.
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 


# --- Configuration and Setup ---

st.set_page_config(
    page_title="PDF to Excel Converter (PyMuPDF + Tesseract)",
    layout="centered",
    initial_sidebar_state="auto",
)

st.title("📚 PDF to Excel Converter (Tesseract OCR Only)")
st.markdown("This tool uses **PyMuPDF and Tesseract** to reliably extract **Hindi (OCR)** text from all pages and merge the results.")
st.caption("Deployment requires a server that supports system packages like Tesseract.")


# --- Helper Functions ---

def convert_dfs_to_excel_bytes(dataframes):
    """
    Concatenates a list of DataFrames and converts the result into an 
    in-memory Excel file (bytes) with a single sheet.
    """
    if not dataframes:
        return None

    try:
        final_df = pd.concat(dataframes, ignore_index=True)
    except Exception as e:
        st.error(f"Error concatenating tables: {e}")
        return None

    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name="Merged_OCR_Result", index=False)
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        st.error(f"Error during Excel conversion: {e}")
        return None


def extract_text_with_ocr(pdf_path, dpi=300):
    """
    Uses PyMuPDF to render each page as an image, runs Tesseract OCR for Hindi,
    and returns a list of DataFrames (one per page).
    """
    extracted_data_blocks = []
    
    try:
        pdf_document = fitz.open(pdf_path)
        num_pages = pdf_document.page_count
        
        st.info(f"PDF has {num_pages} pages. Running OCR on each page... (This will be slow)")
        
        for i in range(num_pages):
            page = pdf_document.load_page(i)
            
            # Render the page to a high-resolution image (PixMap)
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            
            # Convert PixMap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Run Tesseract OCR on the image for Hindi text
            text = pytesseract.image_to_string(img, lang='hin')
            
            lines = text.split('\n')
            
            # Use regex to split by 2 or more spaces, which is robust for OCR output
            page_data = [re.split(r'\s{2,}', line.strip()) for line in lines if line.strip()]
            
            # Only proceed if we actually got data lines
            if page_data:
                page_df = pd.DataFrame(page_data, columns=None) 
                extracted_data_blocks.append(page_df)
            else:
                st.warning(f"No structured text found on page {i+1}.")

        st.success("OCR completed on all pages.")
        return extracted_data_blocks
        
    except pytesseract.TesseractNotFoundError:
        st.error("Tesseract Error: Tesseract executable not found.")
        st.warning("Please ensure **Tesseract** is installed and its path is correct.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during OCR extraction: {e}")
        return None


# --- Streamlit App Logic ---

uploaded_file = st.file_uploader(
    "Upload a PDF file", 
    type=["pdf"], 
    help="Select the PDF containing the data you wish to convert."
)

if uploaded_file is not None:
    pdf_path = None
    dataframes = []
    try:
        with st.spinner("Processing file, rendering pages, and running OCR..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                pdf_path = tmp_file.name

            dataframes = extract_text_with_ocr(pdf_path)
            
            if dataframes and not all(df.empty for df in dataframes):
                st.success("Successfully processed all pages using OCR!")
                
                final_merged_df = pd.concat(dataframes, ignore_index=True)
                
                st.subheader("Merged OCR Result Preview")
                st.dataframe(final_merged_df.head(15))

                excel_bytes = convert_dfs_to_excel_bytes(dataframes) 

                if excel_bytes:
                    st.subheader("Download Result")
                    base_filename = os.path.splitext(uploaded_file.name)[0]
                    st.download_button(
                        label="📥 Download Single Merged Excel File (.xlsx)",
                        data=excel_bytes,
                        file_name=f"{base_filename}_Tesseract_OCR.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                
            else:
                st.warning("No structured text was extracted from the PDF pages after OCR.")
            
    except Exception as e:
        st.error(f"An unexpected error occurred during processing: {e}")
        
    finally:
        if pdf_path and os.path.exists(pdf_path):
             os.unlink(pdf_path)
