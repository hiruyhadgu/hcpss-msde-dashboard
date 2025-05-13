import altair as alt
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from analysis import get_min_max

year_color_map = {
    '2016': '#17becf',   # teal/cyan
    '2017': '#bcbd22',   # olive green
    '2018': '#1f77b4',   # blue
    '2019': '#ff7f0e',   # orange
    '2020': '#2ca02c',   # green
    '2021': '#d62728',   # red
    '2022': '#9467bd',   # purple
    '2023': '#8c564b',   # brown
    '2024': '#e377c2'    # pink
}

def lighten(color, factor=0.3):
        c = mcolors.to_rgb(color)
        return mcolors.to_hex([(1 - factor) * ch + factor for ch in c])

def darken(color, factor=0.1):
    c = mcolors.to_rgb(color)
    return mcolors.to_hex([ch * (1 - factor) for ch in c])


def plot_bar_by_year(df, y_param, category_label="Student Category", color_param="Year", title=""):
    if y_param == "Eco. Disadv_Count":
        y_param = "Eco_Disadv_Count"
        df = df.rename(columns={"Eco. Disadv_Count": "Eco_Disadv_Count"})
    df['Year'] = df['Year'].astype(str)  # Ensure 'Year' is treated as a string for categorical x-axis
    # Create a bar chart with Year on the x-axis and the specified y_param on the y-axis
    # Use the specified color parameter for coloring the bars
    # Set the color parameter to be the same as the y_param if not specified
    df[y_param] = df[y_param].astype(str)  # Ensure y_param is treated as a string for categorical y-axis
    return alt.Chart(df).mark_bar().encode(
        x=alt.X("Year:O", title="Year"),
        y=alt.Y(y_param, title=category_label),
        color=color_param
    ).properties(title=title).interactive()


def pie_chart(df):
    # Clean the column: ensure numeric and strip whitespace
    df["Percent of Students"] = pd.to_numeric(
        df["Percent of Students"], errors="coerce"
    )
    df =df[df['Student Category']!='All Students']
    # Calculate the total sum of existing values
    total_sum = df['Percent of Students'].sum(skipna=True)
    
    # Identify missing values (either NaN or '*')
    missing_categories = df[df['Percent of Students'].isna()]['Student Category'].tolist()

    # Calculate the missing percentage
    missing_value = 100 - total_sum
    df = df[['Student Category', 'Percent of Students']]
    # Add a row for the combined missing categories
    
    if missing_value > 0:
        new_row = pd.DataFrame([{
            'Student Category': 'Combined Missing Categories',
            'Percent of Students': missing_value
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    # Filter out 'All Students' and drop missing data
    df_plot = df[df["Percent of Students"].notnull()]

    pie_chart = alt.Chart(df_plot).mark_arc().encode(
                    theta=alt.Theta(field='Percent of Students', type='quantitative'),  # Proportion of the arc
                    color=alt.Color(field='Student Category', type='nominal'),  # Color by category
                    tooltip=['Student Category', 'Percent of Students']  # Tooltip for interactivity
                ).properties(
                    title='Adjusted Pie Chart with Missing Values')
    return  pie_chart, missing_categories


def line_chart(df, percent_col, grouping=None, demo_category=None, selected_school = None):
    if demo_category:
        title_insert = demo_category + ' Students' if 'students' not in demo_category.lower() else demo_category
    elif selected_school:
        title_insert = selected_school
    else:
        title_insert = grouping
    line_chart = alt.Chart(df).mark_line(point=True).encode(
                    x=alt.X('Year:O', title='Year'),  # Ordinal scale for discrete years
                    y=alt.Y(f'{percent_col}:Q', title=f'{percent_col}'),  # Quantitative scale
                    color=alt.Color(f'{grouping}:N', title=f'{grouping}'),  # Color based on the selected indicator
                    detail=f'{grouping}:N',
                    tooltip=['Year', percent_col]  # Add tooltips for interactivity
                ).properties(
                    title=f'{percent_col} over the years for {title_insert}',
                    width='container',  # Dynamic sizing to fit Streamlit container
                    height=400
                )
     
    return line_chart

def plot_bar_chart(df, x_param, y_param, selected_year, selected_school_level, select_indicator=None):

    if select_indicator:
        df_plot = df[df['Indicator'] == select_indicator]
        get_values = get_min_max(df_plot, 'School_Name', 'Percent_Earned_Points')
    else:
        df_plot = df
        get_values = get_min_max(df_plot, 'School_Name', y_param)
        select_indicator = y_param

    bar_chart = alt.Chart(df_plot).mark_bar().encode(
            x=alt.X(f'{x_param}:O', sort = 'y', title=f'{x_param}'),  # Ordinal scale for discrete years
            y=alt.Y(f'{y_param}:Q',  title=f'{y_param}'),  # Quantitative scale
            color=alt.value(year_color_map[selected_year]),
            tooltip=[f'{x_param}', f'{y_param}']  # Add tooltips for interactivity
        ).properties(
            title=f'{select_indicator} for all {selected_school_level} Schools in {selected_year}',
            width='container',  # Dynamic sizing to fit Streamlit container
            height=400
        )
    
    footer_data = pd.DataFrame({'dummy': [0]})

    footer_chart = (
        alt.Chart(footer_data)
        .mark_text(align="left", baseline="top", fontSize=16, lineBreak="\n")
        .encode(
            # Set the text to a constant string
            text=alt.value(
                f"Highest {select_indicator} | {get_values['highest school']} - ({get_values['highest value']:.2f})\n"
                f"Lowest {select_indicator}  | {get_values['lowest school']} - ({get_values['lowest value']:.2f})"
            ), x=alt.value(0)
        )
        .properties(height=20, width=400)  # set width if needed
    )

    # Vertically concatenate the main chart and the footer
    final_chart = alt.vconcat(bar_chart, footer_chart)
    return final_chart

def plot_stacked_bar_chart(df, x_param, y_param, selected_year, selected_school_level, stack_variable):
    # Create the Altair chart     
            base_color = year_color_map[selected_year]

            spending_type_color_map = {
                'Federal Amount': lighten(base_color, 0.3),
                'State/Local Amount': darken(base_color, 0.1)
            }
            color_scale = alt.Scale(
                domain=['Federal Amount', 'State/Local Amount'],
                range=[spending_type_color_map['Federal Amount'], spending_type_color_map['State/Local Amount']]
            )
            stacked_bar = alt.Chart(df).mark_bar().encode(
                x=alt.X(f'{x_param}:N', sort = 'y', title=f'{x_param}'),
                y=alt.Y(f'{y_param}:Q', title=f'{y_param}'),
                color=alt.Color(f'{stack_variable}:N', scale = color_scale, title='Spending Type'),
                tooltip=[f'{x_param}', f'{y_param}', f'{stack_variable}']
            ).properties(
                title=f'Per-Pupil Expenditure by Spending Type | {selected_year} | {selected_school_level}',
                width='container',
                height=400)
            
            footer_data = pd.DataFrame({'dummy': [0]})
            # highest federal fund recepient
            spending_types = ['Federal Amount','State/Local Amount','Percent_Federal_Expenditure', 'Percent_Local_State_Expenditure']
            get_values = get_min_max(df, 'School_Name', 'Expenditure', 'Spending Type',*spending_types)
            
            # Create a 1-row DataFrame with the text you'd like to display
            footer_chart = (
                alt.Chart(footer_data)
                .mark_text(align="left", baseline="top", fontSize=16, lineBreak="\n")
                .encode(
                    # Set the text to a constant string
                    text=alt.value(
                        f"Highest State and Local Fund Receipient: {get_values['State/Local Amount highest school']} with ${get_values['State/Local Amount highest value']:,.2f} ({get_values['Percent_Local_State_Expenditure highest value']}%)\n"
                        f"Lowest State and Local Fund Receipient: {get_values['State/Local Amount lowest school']} with ${get_values['State/Local Amount lowest value']:,.2f} ({get_values['Percent_Local_State_Expenditure lowest value']}%)\n\n"
                        f"Highest Federal Fund Receipient: {get_values['Federal Amount highest school']} with ${get_values['Federal Amount highest value']:,.2f} ({get_values['Percent_Federal_Expenditure highest value']}%)\n"
                        f"Lowest Federal Fund Receipient: {get_values['Federal Amount lowest school']} with ${get_values['Federal Amount lowest value']:,.2f} ({get_values['Percent_Federal_Expenditure lowest value']}%)"
                    ), x=alt.value(0)
                )
                .properties(height=20, width=400)  # set width if needed
            )

            # Vertically concatenate the main chart and the footer
            final_chart = alt.vconcat(stacked_bar, footer_chart)

            return final_chart