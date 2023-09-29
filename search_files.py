import glob
import shutil

# Для поиска файлов по именам из текстового файла
# Open the text file containing search masks
with open('search_masks.txt', 'r', encoding='UTF-8') as f:
    # Read the contents of the file
    search_masks = f.read().splitlines()

# Search for files in the results subfolder that match the search masks
for mask in search_masks:
    files = glob.glob(f'results/{mask}')

    # Copy the matching files to the temp subfolder
    for file in files:
        shutil.copy(file, 'temp/')
