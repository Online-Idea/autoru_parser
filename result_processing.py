import os
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Protection, Font
from openpyxl.utils import get_column_letter
from pandas import DataFrame


def dealer_data(cars: list[dict]) -> DataFrame:
    """
    Обработка данных одного дилера
    @param cars: лист словарей с данными автомобилей
    @return: Pandas DataFrame с автомобилями дилера
    """
    df = pd.DataFrame.from_records(cars)

    # Позиция
    df['position'] = df.groupby(['mark_model', 'complectation', 'modification', 'year']).cumcount() + 1

    # Чищу цены
    df['price_with_discount'] = df['price_with_discount'].str.replace(r'\D+', '', regex=True)
    df['price_no_discount'] = df['price_no_discount'].str.replace(r'\D+', '', regex=True)

    # Меняю типы
    df[['year', 'price_with_discount', 'price_no_discount']] = \
        df[['year', 'price_with_discount', 'price_no_discount']] \
            .apply(lambda x: pd.to_numeric(x, errors='coerce'))

    # Сортирую
    df = df.sort_values(by=['mark_model', 'complectation', 'modification', 'year', 'price_with_discount'])

    # Количество автомобилей
    df_in_stock = df[df['in_stock'] == 'В наличии']
    count_df = df_in_stock.groupby(['mark_model', 'complectation', 'modification', 'year', 'dealer']) \
        .size().reset_index(name='stock')
    df = pd.merge(df, count_df, on=['mark_model', 'complectation', 'modification', 'year', 'dealer'], how='left')

    df_for_order = df[df['in_stock'].isin(['В пути', 'На заказ'])]
    count_df = df_for_order.groupby(['mark_model', 'complectation', 'modification', 'year', 'dealer']) \
        .size().reset_index(name='for_order')
    df = pd.merge(df, count_df, on=['mark_model', 'complectation', 'modification', 'year', 'dealer'], how='left')

    # Удаляю дубликаты
    # df = df.drop_duplicates(subset=['mark_model', 'complectation', 'modification', 'year'])
    df = df.drop_duplicates(subset=['mark_model', 'complectation', 'modification', 'year', 'dealer'])

    return df


def dealers_pandas(df: DataFrame, autoru_name: str) -> str:
    """
    Здесь обработка данных, собранных со страниц дилеров
    @param df: Pandas DataFrame с данными дилеров
    @param autoru_name: имя клиента на авто.ру
    @return: имя готового файла
    """
    # Удаляю ненужные столбцы
    df = df.drop(columns=['condition', 'in_stock'])

    # Считаю разницу
    lookup_df = df[df['dealer'] == autoru_name]
    merged_df = pd.merge(df, lookup_df, on=['mark_model', 'complectation', 'modification', 'year'],
                         suffixes=('_data', '_lookup'), how='left')
    merged_df['price_with_discount_difference'] = merged_df['price_with_discount_data'] - merged_df[
        'price_with_discount_lookup']
    merged_df['price_no_discount_difference'] = merged_df['price_no_discount_data'] - merged_df[
        'price_no_discount_lookup']

    # Удаляю столбцы по которым считал разницы
    merged_df = merged_df.filter(regex='^(?!.*_lookup)')

    # Убираю более ненужные суффиксы
    merged_df.columns = merged_df.columns.str.replace('_data', '')

    # Сортировка
    merged_df = merged_df.sort_values(
        by=['mark_model', 'complectation', 'modification', 'year', 'price_with_discount'])

    # Меняю столбцы местами
    merged_df = merged_df[['mark_model', 'complectation', 'modification', 'year', 'dealer',
                           'price_with_discount', 'price_no_discount',
                           'price_with_discount_difference', 'price_no_discount_difference',
                           'position', 'link', 'stock', 'for_order']]

    merged_df = merged_df.fillna('')

    # Очищаю повторы данных автомобиля чтобы лучше смотрелось
    merged_df.loc[merged_df['mark_model'].duplicated(), 'mark_model'] = ''
    is_duplicate = merged_df.duplicated(subset=['complectation', 'modification', 'year'], keep='first')
    merged_df.loc[is_duplicate, 'complectation'] = ''
    merged_df.loc[is_duplicate, 'modification'] = ''
    merged_df.loc[is_duplicate, 'year'] = ''

    # Перевожу имена столбцов
    merged_df = merged_df.rename(columns={
        'mark_model': 'Марка, модель',
        'complectation': 'Комплектация',
        'modification': 'Модификация',
        'year': 'Год',
        'dealer': 'Имя дилера',
        'price_with_discount': 'Цена со скидками',
        'price_no_discount': 'Цена без скидок',
        'price_with_discount_difference': 'Разница цены со скидками',
        'price_no_discount_difference': 'Разница цены без скидок',
        'position': 'Позиция',
        'stock': 'В наличии',
        'for_order': 'Под заказ',
        'link': 'Ссылка',
    })

    # Сохраняю
    file_name = 'after_pandas.xlsx'
    merged_df.T.reset_index().T.to_excel(file_name, sheet_name='Все', header=False, index=False)
    return file_name


def data_work(cars, dealer):
    # Обрабатываю результат
    df = pd.DataFrame.from_records(cars)

    # Меняю типы
    df[['year', 'min_price_with_discount', 'min_price_no_discount', 'max_price', 'stock', 'for_order']] = \
        df[['year', 'min_price_with_discount', 'min_price_no_discount', 'max_price', 'stock', 'for_order']] \
            .apply(pd.to_numeric)

    # Удаляю Рынок т.к. самый дешёвый будет виден по сортировке
    index_to_drop = df[df['dealer'] == 'Рынок'].index
    df = df.drop(index_to_drop)

    # Этот dataframe используется для столбцов разницы
    lookup_df = df[df['dealer'] == dealer]
    merged_df = pd.merge(df, lookup_df, on=['mark_model', 'complectation', 'modification', 'year'],
                         suffixes=('_data', '_lookup'))
    merged_df['min_price_with_discount_difference'] = merged_df['min_price_with_discount_data'] - merged_df[
        'min_price_with_discount_lookup']
    merged_df['min_price_no_discount_difference'] = merged_df['min_price_no_discount_data'] - merged_df[
        'min_price_no_discount_lookup']
    merged_df['max_price_difference'] = merged_df['max_price_data'] - merged_df['max_price_lookup']

    # Сортировка
    merged_df = merged_df.sort_values(
        by=['mark_model', 'complectation', 'modification', 'year', 'min_price_with_discount_data'])

    # Удаляю столбцы по которым считал разницы
    merged_df = merged_df.filter(regex='^(?!.*_lookup)')

    merged_df.columns = merged_df.columns.str.replace('_data', '')

    # Меняю столбцы местами
    merged_df = merged_df[['mark_model', 'complectation', 'modification', 'year', 'dealer',
                           'min_price_with_discount', 'min_price_no_discount', 'max_price',
                           'min_price_with_discount_difference', 'min_price_no_discount_difference',
                           'max_price_difference', 'stock', 'for_order', 'link']]

    merged_df = merged_df.fillna('')

    # Удаляю строки с пустыми ценами
    merged_df = merged_df.drop(merged_df[(merged_df['max_price'] == '') &
                                         (merged_df['max_price_difference'] == '')].index)

    # Очищаю повторы данных автомобиля чтобы лучше смотрелось
    merged_df.loc[merged_df['mark_model'].duplicated(), 'mark_model'] = ''
    is_duplicate = merged_df.duplicated(subset=['complectation', 'modification', 'year'], keep='first')
    merged_df.loc[is_duplicate, 'complectation'] = ''
    merged_df.loc[is_duplicate, 'modification'] = ''
    merged_df.loc[is_duplicate, 'year'] = ''

    # Перевожу имена столбцов
    merged_df = merged_df.rename(columns={
        'mark_model': 'Марка, модель',
        'complectation': 'Комплектация',
        'modification': 'Модификация',
        'year': 'Год',
        'dealer': 'Имя дилера',
        'min_price_with_discount': 'Мин. цена со скидками',
        'min_price_no_discount': 'Мин. цена без скидок',
        'max_price': 'Макс. цена',
        'min_price_with_discount_difference': 'Разница мин. цена со скидками',
        'min_price_no_discount_difference': 'Разница мин. цена без скидок',
        'max_price_difference': 'Разница макс. цена',
        'stock': 'В наличии',
        'for_order': 'Под заказ',
        'link': 'Ссылка',
    })

    file_name = 'after_pandas.xlsx'
    merged_df.T.reset_index().T.to_excel(file_name, sheet_name='Все', header=False, index=False)
    return file_name


def format_work(xlsx_file: str, autoru_name: str, client: str) -> str:
    """
    Форматирование готового файла в читабельный вид
    @param xlsx_file: xlsx файл после dealers_pandas
    @param autoru_name: имя клиента на авто.ру
    @param client: имя нашего клиента
    @return: путь к файлу
    """
    # Форматирование результата
    book = load_workbook(xlsx_file)
    worksheet = book['Все']

    # Буквы нужных столбцов
    price_cols = []
    difference_cols = []
    stock_cols = []
    for col in range(1, worksheet.max_column + 1):
        cell = worksheet.cell(row=1, column=col).value
        col_letter = get_column_letter(col)
        if cell == 'Имя дилера':
            dealer_col = col_letter
        elif 'цен' in cell.lower():
            price_cols.append(col_letter)
        elif cell == 'Ссылка':
            link_col = col_letter
        elif cell == 'В наличии' or cell == 'Под заказ':
            stock_cols.append(col_letter)
        elif 'Позиция' in cell:
            position_col = col_letter

        if 'Разница' in cell:
            difference_cols.append(col_letter)

    # Меняю ширину столбцов
    for column in worksheet.columns:
        worksheet[column[0].coordinate].alignment = Alignment(wrap_text=True)
        max_length = 0
        column_name = column[0].column_letter

        if column_name == link_col:
            worksheet.column_dimensions[column_name].width = 20
        elif column_name in price_cols or column_name in stock_cols or column_name == position_col:
            worksheet.column_dimensions[column_name].width = 13
        else:
            for cell in column:
                if cell.row == 1:
                    continue
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_name].width = adjusted_width

    # Цвета заливок
    blue_fill = PatternFill(start_color='DEE6EF', end_color='DEE6EF', fill_type='solid')
    red_fill = PatternFill(start_color='E0C2CD', end_color='E0C2CD', fill_type='solid')
    green_fill = PatternFill(start_color='DDE8CB', end_color='DDE8CB', fill_type='solid')
    font = Font(name="Calibri", bold=True)

    # Выделяю голубым нашего дилера
    for row in range(2, worksheet.max_row + 1):
        if worksheet[dealer_col + str(row)].value == autoru_name:
            prices_range = worksheet[f'{dealer_col}{str(row)}:{price_cols[-1]}{str(row)}']
            for cell in prices_range[0]:
                cell.fill = blue_fill
                # cell.font = font

        # Выделяю красным тех кто дешевле нас и зеленым тех кто дороже нас
        for col in difference_cols:
            cell = worksheet[col + str(row)]
            if cell.value:
                if cell.value < 0:
                    cell.fill = red_fill
                elif cell.value > 0:
                    cell.fill = green_fill

    # Высота первой строки в 3 строки
    worksheet.row_dimensions[1].height = 45

    # Выравнивание по центру первой строки и жирный шрифт
    for cell in worksheet[1]:
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.font = font

    # Закрепляю строки и столбцы
    worksheet.freeze_panes = 'C2'

    today = datetime.now().strftime('%d.%m.%Y')
    file_name = f'Сравнение {client} {today}.xlsx'
    file_path = os.path.join('results', file_name)
    book.save(file_path)
    return file_path
