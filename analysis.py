import pandas as pd
import numpy as np

def get_demo_summary(df, year_col, school_name_col, selected_year, selected_school):
    
    df = df.copy()
    df = df.astype({year_col: int})
    df = df[(df[year_col] == selected_year) & (df[school_name_col] == selected_school)]
    df['All Students'] = df['All Students'].str.replace(',', '', regex=False)
    df = df.melt(
        id_vars=[year_col, school_name_col],
        var_name="Student Category",
        value_name="Number of Students"
    )
    df['Number of Students'] = pd.to_numeric(df['Number of Students'], errors='coerce')

    all_students_row = df[df['Student Category'] == 'All Students']
  
    if all_students_row.empty:
        raise ValueError("Missing 'All Students' row.")

    all_students = all_students_row['Number of Students'].values[0]
    
    df['Percent of Students'] = (df['Number of Students'] / all_students * 100).round(2)
 
    return df


def separate_count_and_percent(df, id_cols=('Year', 'School_Name')):
    count_columns = [col for col in df.columns if col.endswith('_Count')]
    percent_columns = [col for col in df.columns if col.endswith('%')]

    count_df = df[list(id_cols) + count_columns].copy().melt(
        id_vars=id_cols, var_name="Student Category", value_name="Number of Students"
    )
    percent_df = df[list(id_cols) + percent_columns].copy().melt(
        id_vars=id_cols, var_name="Student Category", value_name="Percent of Students"
    )

    count_df["Student Category"] = count_df["Student Category"].str.replace('_Count', '', regex=False)
    percent_df["Student Category"] = percent_df["Student Category"].str.replace('%', '', regex=False)

    return count_df, percent_df


def get_student_group_summary(df, year_col, school_name_col, selected_year, selected_school, school_level):
    count_df, percent_df = separate_count_and_percent(df)

    count_df = count_df[
        (count_df[year_col] == selected_year) & (count_df[school_name_col] == selected_school) & (count_df[school_name_col].str.contains(school_level))
    ].reset_index(drop=True)

    percent_df = percent_df[
        (percent_df[year_col] == selected_year) & (percent_df[school_name_col] == selected_school) & (percent_df[school_name_col].str.contains(school_level))
    ].reset_index(drop=True)

    return count_df.join(percent_df[["Percent of Students"]])

def get_min_max(df, school_name_col, percent_col, filter_value=None, *args):
    df = df.replace('na', np.nan, regex=True)
    returned_dict = {}
    if filter_value:
        for arg in args:
            filtered_df = df[df[filter_value] == arg]
            highest_school, highest_value, lowest_school, lowest_value = min_max_func(filtered_df, school_name_col, percent_col)
            returned_dict[f'{arg} highest school'] = highest_school
            returned_dict[f'{arg} highest value'] = highest_value
            returned_dict[f'{arg} lowest school'] = lowest_school
            returned_dict[f'{arg} lowest value'] = lowest_value
    else:
          highest_school, highest_value, lowest_school, lowest_value = min_max_func(df, school_name_col, percent_col)
          returned_dict['highest school'] = highest_school
          returned_dict['highest value'] = highest_value
          returned_dict['lowest school'] = lowest_school
          returned_dict['lowest value'] = lowest_value
    return returned_dict

def min_max_func(df, school_name_col, percent_col):
    # Locate the school with the minimum value for the selected indicator
    highest_school = df.loc[df[percent_col].astype(float).idxmax()][school_name_col]

    # Get the lowest value for the selected indicator
    highest_value = float(df.loc[df[percent_col].astype(float).idxmax()][percent_col])

    # Locate the school with the minimum value for the selected indicator
    lowest_school = df.loc[df[percent_col].astype(float).idxmin()][school_name_col]

    # Get the lowest value for the selected indicator
    lowest_value = float(df.loc[df[percent_col].astype(float).idxmin()][percent_col])

    return highest_school, highest_value, lowest_school, lowest_value