import os
import win32com.client as win32

# Function to convert .xlsx to .xls with formatting
def convert_xlsx_to_xls_with_formatting(xlsx_file, xls_file):
    try:
        excel = win32.gencache.EnsureDispatch('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False  # Suppress any alerts

        # Open the workbook and convert to .xls
        wb = excel.Workbooks.Open(os.path.abspath(xlsx_file))
        wb.SaveAs(os.path.abspath(xls_file), FileFormat=56)  # 56 is the format code for .xls
        wb.Close(False)
    except Exception as e:
        print(f"Failed to convert {xlsx_file} to {xls_file}: {e}")
    finally:
        excel.Application.Quit()

# Directory containing the .xlsx files
input_directory = 'temp'  # Change this to your directory
output_directory = 'out'  # Change this to your desired output directory

# Create output directory if it doesn't exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Convert all .xlsx files in the directory to .xls
for filename in os.listdir(input_directory):
    if filename.endswith('.xlsx'):
        xlsx_path = os.path.join(input_directory, filename)
        xls_filename = filename.replace('.xlsx', '.xls')
        xls_path = os.path.join(output_directory, xls_filename)

        convert_xlsx_to_xls_with_formatting(xlsx_path, xls_path)
        print(f"Converted: {filename} to {xls_filename}")

print("Conversion complete!")
