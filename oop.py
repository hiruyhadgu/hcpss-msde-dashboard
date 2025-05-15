import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import sqlite3
import matplotlib.pyplot as plt
from analysis import get_demo_summary, get_student_group_summary, get_min_max
from charts import plot_bar_by_year, pie_chart, line_chart, plot_bar_chart, plot_stacked_bar_chart

st.set_page_config(page_title="HCPSS MSDE Dashboard 2016 - 2024", page_icon=":chart_with_upwards_trend:", layout="wide")

st.logo("hh.png")


class SqlReader:
    def __init__(self, table_name):
        self.table_name = table_name

    def read(self):
        # Connect to the SQLite database
        conn = sqlite3.connect("school_data.db")

        # Load the overall performance data from the database
        self.df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)

        # Close the database connection
        conn.close()

        # Return the loaded DataFrames
        return self.df

class FileInfo(SqlReader):
    def __init__(self, table_name):
        super().__init__(table_name)  # inherit from CsvReader properly
        self.original_df = self.read()  # Always preserved
        self.df = self.original_df.copy()  # Used for filtering, display, etc.
        self.columns = self.df.columns.tolist()
        self.columns = self.df.columns

    def reset(self):
        """Reset working df to the original state."""
        self.df = self.original_df.copy()
        return self
    
    def get_columns(self):
        return self.columns
    
    def display_school_level(self, level):
        self.df = self.df[self.df['School_Name'].str.contains(level)|self.df['School_Level'].str.contains(level)]
        return self.df
    
    def display_year(self, year):
        self.df = self.df[self.df['Year'] == year]
        return self.df
    
    def filter_by_column_value(self, column, value):
        self.df = self.df[self.df[column] == value]
        return self.df
    
    def filter_by_multiple_columns(self, filters, use_original=False, inplace=False):
        df = self.original_df.copy() if use_original else self.df.copy()
        for column, value in filters.items():
            df = df[df[column] == value]
        if inplace:
            self.df = df
            return self
        else:
            return df
    
    
    def clean_data(self):
        self.df = self.df.dropna()
        return self.df
    
    def get_unique_values(self, column, use_original=False, filter_by_year = None):
        """Get unique values from a column, optionally using original (unfiltered) DataFrame."""
        source_df = self.original_df if use_original else self.df
       
        if filter_by_year is not None:
            source_df = source_df[source_df['Year'].astype(int) == int(filter_by_year)]

        return source_df[column].dropna().unique()
    
    
    def get_year_combinations(self, *years):
        year_combinations =[]

        for year in years:
            for yr in year:
                year_combinations.append(int(yr))
        # Remove duplicates
        year_combinations = list(set(year_combinations))
        # Sort the years
        year_combinations.sort()


        return [int(year) for year in year_combinations]

    def change_data_type(self, **kwargs):
        for column, data_type in kwargs.items():
            if column in self.df.columns:
                if data_type == 'int':
                    self.df[column] = self.df[column].astype(int)
                elif data_type == 'float':
                    self.df[column] = self.df[column].astype(float)
                elif data_type == 'str':
                    self.df[column] = self.df[column].astype(str)
                elif data_type == 'datetime':
                    self.df[column] = pd.to_datetime(self.df[column], errors='coerce')
                elif data_type == 'numeric':
                     # Convert to numeric, handling errors
                    self.df[column] = pd.to_numeric(self.df[column], errors='coerce')
        return self
    
    def compute_percentage(self, numerator_col, denominator_col, output_col):
        self.df[output_col] = (
            self.df[numerator_col]
            .div(self.df[denominator_col].replace(0, pd.NA))
            .mul(100)
            .round(2)
        )
        return self
    
    def get_school_level(self, selected_school_level):
        search_term = selected_school_level if selected_school_level else ~['High, Middle, Elementary']
        self.df = self.df[self.df['School_Name'].str.contains(search_term, na=False)]
        return self
    
    def display(self):
        return self.df

class OverallPerformance(FileInfo):
    def __init__(self, table_name):
        super().__init__(table_name)
        self.df = self.df.rename(columns={'School': 'School_Name'})
        self.df['Indicator'] = self.df['Indicator'].str.replace('TOTAL POINTS:', 'Total Points',case=False, regex=True)
        self.change_data_type(Year='int',Possible_Points='numeric',Earned_Points='numeric')
        self.compute_percentage('Earned_Points', 'Possible_Points', 'Percent_Earned_Points')

       
class AchievementsTable(FileInfo):
    def __init__(self, table_name):
        super().__init__(table_name)
        self.df = self.df.rename(columns={'School': 'School_Name'})
        self.strip_characters('Math_Proficiency', 'ELA_Proficiency')
        self.change_data_type(Math_Proficiency='numeric',ELA_Proficiency='numeric', Year='int')
    def strip_characters(self, *args):
        for column in args:
            self.df[column] = self.df[column].str.replace('%', '', regex = False)
            self.df[column] = self.df[column].str.replace('<= 5.0', '5.0', regex = False)
            self.df[column] = self.df[column].str.replace('NA', '', regex = False)
            
        return self

class SchoolDemo(FileInfo):
    def __init__(self, table_name):
        super().__init__(table_name)
        self.df["School_Level"] = self.df["School_Name"].astype(str).apply(
            lambda name: (
                "Elementary" if "elementary" in name.lower() else
                "Middle" if "middle" in name.lower() else
                "High" if "high" in name.lower() else
                "Other"
            )
        )

class StudentGroupPopulations(FileInfo):
    def __init__(self, file):
        super().__init__(file)
        
    def strip_whitespace(self):
        self.df = self.df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        return self
    
class PerStudentExpenditure(FileInfo):
    def __init__(self, table_name):
        super().__init__(table_name)
        self.df['Percent_Local_State_Expenditure'] =(self.df['State/Local Amount'] / self.df['Total Amount']*100).round(2)
        self.df['Percent_Federal_Expenditure'] =(self.df['Federal Amount'] / self.df['Total Amount']*100).round(2)
        self.df = self.df.rename(columns={'School Name': 'School_Name'})

    def melt_data(self):
        self.df = self.df.drop('Total Amount', axis = 1)
        self.df = self.df.melt(id_vars = ['Year', 'School','School_Name', 'School Level'],
                                var_name = 'Spending Type',
                                value_name = 'Expenditure')
        return self

class StudentDemographicData:

    def __init__(self):
        self.student_demographic_data = pd.DataFrame()
    
    def combine_demo_student_group(self, df1, df2):
        self.student_demographic_data = pd.concat([df1, df2], axis=0, ignore_index=True).drop(columns=['Year', 'School_Name'])
        self.student_demographic_data = self.student_demographic_data.dropna()

        return self
    
    def process_for_piechart(self, selected_year, selected_school):
        self.filter_by_multiple_columns({'Year': str(selected_year), 'School_Name': selected_school})

        return self

    def display(self):
        return self.student_demographic_data

class ClassSize(FileInfo):
    def __init__(self, table_name):
        super().__init__(table_name)

    def melt_data(self):
        self.df = self.df.melt(id_vars = ['Year', 'School_Name', 'School_Level'],
                                var_name = 'Category',
                                value_name = 'Class_Size')
        return self
    
class DataDashboard:
    def __init__(self, expander_title, subheaders=None, column_layouts=None):
        """
        Parameters:
        - expander_title: Title of the expander
        - subheaders: Optional list of subheaders (one for each column group)
        - column_layouts: List of ints (e.g., [2, 3]) or lists (e.g., [[2, 1], 3])
        """
        self.expander_title = expander_title
        self.subheaders = subheaders or []
        self.column_layouts = column_layouts or []

    def open_expander(self):
        return st.expander(self.expander_title, expanded=True)

    def render_columns(self):
        column_groups = []

        for i, layout in enumerate(self.column_layouts):
            if i < len(self.subheaders):
                st.subheader(self.subheaders[i])

            # Handle layout as either an integer or list of weights
            if isinstance(layout, int):
                column_group = st.columns(layout)
            elif isinstance(layout, (list, tuple)):
                column_group = st.columns(layout)
            else:
                raise ValueError(f"Invalid layout: {layout}")

            column_groups.append(column_group)

        return column_groups  # list of column groups

class Sidebar:
    def __init__(self, title ,instructions, header):
        self.instructions = instructions
        self.title = title
        self.header = header
        self.sidebar = st.sidebar
        self.sidebar.title(title)
        self.sidebar.write(instructions)
        self.sidebar.markdown("---")
    
    def add_selectbox(self, label, options, key=None):
        return self.sidebar.selectbox(label, options, key=key)
    
    def add_multiselect(self, label, options):
        return self.sidebar.multiselect(label, options)
    
    def add_slider(self, label, min_value, max_value):
        return self.sidebar.slider(label, min_value, max_value)

overall_performance = OverallPerformance('overall_performance')
achievements_table = AchievementsTable('achievements_table')
student_group_populations = StudentGroupPopulations('student_group_populations')
school_info = FileInfo('school_info')
school_demo = SchoolDemo('school_demographics')
per_student_expenditure = PerStudentExpenditure('per_student_expenditure')
class_size = ClassSize('class_size')
student_group_populations.strip_whitespace()


# # Load the data
intro_container = st.container()
sidebar_container = st.container()
section1_container = st.container()
section2_container = st.container()
section3_container = st.container()
section4_container = st.container()
section5_container = st.container()
section6_container = st.container()

with sidebar_container:
# Create a sidebar
    side_bar = Sidebar("Navigation", "Use the sidebar to navigate the dashboard.",'Select School and Year to View')
    yr1 =overall_performance.get_unique_values('Year')
    yr2 = student_group_populations.get_unique_values('Year')
    y3 = class_size.get_unique_values('Year')
    year_combinations = overall_performance.get_year_combinations(yr1, yr2, y3)

    selected_year = side_bar.add_selectbox("Select Year:", year_combinations, key=1)

    selected_school_level = side_bar.add_selectbox("Select School Level:",school_info.get_unique_values('School_Level'), key=2)
    school_info.display_school_level(selected_school_level)
    selected_school = side_bar.add_selectbox("Select School:", school_info.get_unique_values('School_Name'), key=3)

with intro_container:
    st.title('HCPSS MSDE Dashboard 2016 - 2024')
    
    st.write(
    "The Maryland State Department of Education (MSDE) is a public education agency responsible for overseeing the state's public schools. "
    "Every year the MSDE releases a report card for each public school in the state. The report card includes demographic data for each school. "
    "For each school, the report also includes various achievement and proficiency metrics. Additionally, the report card includes per student expenditure data. "
    "This app provides the ability to view the data in a user-friendly way. It allows users to view student report cards and demographic data for different years and schools.")

    st.markdown("""
    To view the data, use the sidebar to select a school and year.  
    The sidebar also allows you to view the data for different school levels.

    **Sections:**
    - **Section 1:** Demographic data for selected schools and years  
    - **Section 2:** Achievement and proficiency data  
    - **Section 3:** Comparison of indicators and scores  
    - **Section 4:** Per student expenditure data  
    - **Section 5:** Class size data
    """)

    st.markdown("---")


with section1_container:

    st.markdown("**SECTION 1: DEMOGRAPHIC DATA**")
    st.write("The Demographic Data section displays the number of students in each demographic category for a selected school and year. "
                "The Per Student Expenditure section displays the per student expenditure for a selected school and year. "
                "Note that student demographic data is only available for 2020 thru 2024 and Per Student Expenditure data is only available for 2019 thru 2023.")

    
    no_demo = False
    demographic_data = DataDashboard("Click this Section to Explore Demographic Data", 
                                    ["Shool Report Card and Demographics at a Glance", 
                                     f"{selected_school} | {selected_year} | Demographic Data"], [2])
        
    if str(selected_year) not in school_demo.get_unique_values('Year', True) or selected_school not in school_demo.get_unique_values('School_Name', True, filter_by_year=int(selected_year)):
        no_demo = True
    else:
        
        sub_school_demo = get_demo_summary(school_demo.df,'Year', 'School_Name', selected_year, selected_school)
        sub_student_group_populations = get_student_group_summary(student_group_populations.df,"Year","School_Name", selected_year, selected_school, selected_school_level)
        student_demographic_data = StudentDemographicData()
        student_demographic_data.combine_demo_student_group(sub_school_demo, sub_student_group_populations)

    with demographic_data.open_expander():
        column_groups = demographic_data.render_columns()
        col1, col2=column_groups[0]
    
    
        
        with col1:
            st.markdown("Some Notes on Demographic Data")
            st.caption("""
                * Values of '*' or 'None'/'null' for *Number of Students* indicates that the number of students is less than 10. 
                * Values of 'assigned *' indicate that the school does not have that category of student.
                * Values of 'undefined' indicate that the school does not have that category of student.
                """)
            if no_demo:
                st.warning(f"No demographic data available for {selected_year}. Data available for 2020 thru 2024")
            else:
                st.dataframe(student_demographic_data.display(), hide_index=True)

            try:
                st.write("Per Pupil Expenditure")
                per_student_expenditure_for_school = per_student_expenditure.filter_by_multiple_columns({'School_Name': selected_school, 'Year': selected_year})
                transposed_df = per_student_expenditure_for_school.drop(columns = ['Year','School', 'School_Name', 'School Level'], axis = 1).T.rename(columns = {per_student_expenditure_for_school.index[0]:'Spending Type'})
                st.dataframe(transposed_df)
            except Exception as e:
                st.warning(f'Per Student Expenditure Data Not Available for {selected_school} in {selected_year}.')
        with col2:
            if no_demo:
                st.warning(f"No demographic data available for {selected_year}. Data available for 2020 thru 2024")
            else:
                try:
                    options = student_demographic_data.display()['Student Category'].dropna().unique()
                    select_to_plot = st.selectbox("Select Student Category:",options, key=4)
                    school_demo_to_plot = school_demo.filter_by_column_value('School_Name',selected_school)
                    student_group_populations=student_group_populations.filter_by_column_value('School_Name',selected_school)
                    

                    if select_to_plot in school_demo.columns.unique():
                        to_plot = school_demo_to_plot
                        y_param = select_to_plot
                        # school_demo[select_to_plot] = school_demo[select_to_plot].astype('float')
                
                    elif any(select_to_plot in col for col in student_group_populations.columns.unique()):
                        to_plot = student_group_populations
                        y_param = f'{select_to_plot}_Count'
                    
                    chart = plot_bar_by_year(to_plot, y_param, category_label="Student Category", color_param="Year", title="")
                    st.altair_chart(chart, use_container_width=True)
                # st.dataframe(school_demo, hide_index=True
                    
                except Exception as e:
                    st.warning(f"No demographic data available for {selected_year}. Data available for 2020 thru 2024")
                try:

                    chart, missing_categories = pie_chart(sub_school_demo)
                    st.altair_chart(chart, use_container_width=True)
            
                    if missing_categories:
                        st.warning(f"The following categories had missing values and were combined into 'Combined Missing Categories': {', '.join(missing_categories)}")
                except Exception as e:
                    st.warning(f"No demographic data available for {selected_year}. Data available for 2020 thru 2024")
        
    st.markdown("---")
with section2_container:

    st.markdown("**SECTION 2: OVERALL PERFORMANCE AND PROFICIENCY INDICATORS FOR EACH SCHOOL**")
    st.write("The MSDE report card provides so-called performance indicators for each school. "
            "These indicators are Academic Achievement, Academic Progress, Graduation Rate, School Quality and Student Success, "
            "Progress in Achieving English Language Proficiency, Readiness for Post-Secondary Success. These parameters are defined"
            "by the MSDE and are used to evaluate the performance of each school. The section below allows you to explore these parameters"
            "for each school and year.")
    
    academic_achievement_and_overall_performance = DataDashboard("Click this Section to Explore Academic Achievement and Overall Performance Scores for Each School by Year",
                                                                 [f"{selected_school} : Overall Performance", 
                                                                 f"{selected_school} : Math and ELA Proficiency by Student Category"], [2,2,2])
    
    with academic_achievement_and_overall_performance.open_expander():
    
        if selected_year not in overall_performance.get_unique_values("Year", use_original=True).astype(int):
            st.warning(f"Overall Performance Data Not Available for 2016-2017 and 2020-2021.")
            
        else:
            column_groups = academic_achievement_and_overall_performance.render_columns()
            col3, col4 = column_groups[0]
        
            with col3:
                sub_combined_overall_performance = overall_performance.filter_by_multiple_columns({'Year': int(selected_year), 'School_Name': selected_school})
                if sub_combined_overall_performance.empty:
                    st.warning(f"No overall performance data available for {selected_school}")
                else:
                    st.dataframe(sub_combined_overall_performance.drop(columns=['Year', 'School_Name','table_type']), hide_index=True)
            with col4:
                to_plot_indicator = overall_performance.filter_by_multiple_columns({'School_Name': selected_school}).dropna()
                if to_plot_indicator.empty:
                    st.warning(f"No overall performance data available for {selected_school}")
                else:
                    chart = line_chart(to_plot_indicator, 'Percent_Earned_Points', 'Indicator')
                    # Display the chart in Streamlit
                    st.altair_chart(chart, use_container_width=True)
        

        if selected_year not in achievements_table.get_unique_values("Year", use_original=True).astype(int):
            st.warning(f"Math and ELA Proficiency Data Not Available for 2016-2017 and 2020-2021.")
        else:
            
            col5, col6 = column_groups[1]
            with col5:
                st.write("Math and ELA Proficiency by Student Category")
                sub_combined_achievements_table = achievements_table.filter_by_multiple_columns({'Year': int(selected_year), 'School_Name': selected_school})
                if sub_combined_achievements_table.empty:
                    st.warning(f"No overall performance data available for {selected_school}")
                else:
                    st.dataframe(sub_combined_achievements_table.drop(columns=['Year', 'School_Name','table_type']), hide_index=True)
            with col6:
                select_indicator = st.radio("Select Indicator:", options =['Math_Proficiency', 'ELA_Proficiency'], horizontal=True, key=8)
                    
                try:
                    to_plot_indicator = achievements_table.filter_by_multiple_columns({'School_Name': selected_school})
                    if to_plot_indicator.empty:
                        st.warning(f"No overall performance data available for {selected_school}")
                    else:
                
                        chart = line_chart(to_plot_indicator, select_indicator, 'Student_Category')

                        st.altair_chart(chart, use_container_width=True)

                except Exception as e:
                    if no_demo:
                        st.warning(f"No {select_indicator} data available in {selected_year}. Data available for 2020 thru 2024")
                    else:
                        st.warning(f"No {select_indicator} data available for {select_to_plot} Category")
        
    st.markdown("---")

with section3_container:
    st.markdown("**SECTION 3: COMPARISON OF SCHOOL SYSTEM WIDE PERFORMANCE BY SCHOOL LEVEL**")
    st.write("The section below allows you to compare the overall performance of schools at different levels. "
                "You can select the school level and the year to view the overall performance of schools at that level. "
                "You can also compare the proficiency indicators of schools at different levels. ")
    
    school_system_wide_performance = DataDashboard("Click this Section to Explore School System Wide Performance by School Level",
                                                    ["School System Wide Overall Performance by School Level", 
                                                    "School System Wide Achievements by School Level"], [2])
        
    # schools_in_school_level = school_info[school_info["School_Level"]==selected_school_level]
    with school_system_wide_performance.open_expander():
        
        if selected_year not in overall_performance.get_unique_values("Year", use_original=True).astype(int):
                st.warning(f"Overall Performance Data Not Available for 2016-2017 and 2020-2021.")
        
        elif selected_school_level == 'Other':
            st.warning(f"Achievements Data Not Available for Schools in this Category")
                
        else:
            school_level_combined_overall_performance = overall_performance.get_school_level(selected_school_level).filter_by_multiple_columns({'Year': int(selected_year)})
            # search_term = selected_school_level if selected_school_level else ~['High, Middle, Elementary']
            # school_level_combined_overall_performance = school_level_combined_overall_performance[school_level_combined_overall_performance['School_Name'].str.contains(search_term, na=False)]
            column_group = school_system_wide_performance.render_columns()
            select_indicator = st.selectbox("Select Indicator:", school_level_combined_overall_performance['Indicator'].unique(), key=5)
            
            chart = plot_bar_chart(school_level_combined_overall_performance,'School_Name','Percent_Earned_Points', str(selected_year), selected_school_level, select_indicator)
    
            st.altair_chart(chart, use_container_width=True)
           
        st.markdown("---")
        column_group = school_system_wide_performance.render_columns()
        col7, col8 =  column_group[0] 
    
        if  selected_year not in achievements_table.get_unique_values("Year", use_original=True).astype(int):
                st.warning(f"Achievements Data Not Available for 2016-2017 and 2020-2021.")
        elif selected_school_level == 'Other':
            st.warning(f"Achievements Data Not Available for Schools in this Category")
        else:
            
            with col7:
                select_to_plot = st.selectbox("Select Student Category:", achievements_table.get_unique_values('Student_Category', use_original=True), key=6)
            with col8:
                select_indicator = st.selectbox("Select Indicator:", options =['Math_Proficiency', 'ELA_Proficiency'], key=7)
                to_plot_indicator = achievements_table.get_school_level(selected_school_level).filter_by_multiple_columns({'Student_Category': select_to_plot, 'Year': int(selected_year)})
            
            chart = plot_bar_chart(to_plot_indicator,'School_Name',select_indicator, str(selected_year), selected_school_level)
    
            st.altair_chart(chart, use_container_width=True)
        
    st.markdown("---")

with section4_container:
    st.markdown("**SECTION 4: PER STUDENT EXPENDITURE**")
    st.write("The section below allows you to compare the per student expenditure for a selected school and year. "
            "You can select the school level and the year to view the per student expenditure for that school level.")

    per_student_expenditure_display = DataDashboard("Click this Section to Explore Per Student Expenditure",
                                            [f"{selected_school} | {selected_year} | Per Student Expenditure"], [2])

    with per_student_expenditure_display.open_expander():

        

        individual_or_all = st.radio('Select Option:', ['School Level', 'Individual School'], horizontal=True, key = 9)
        per_student_expenditure_school_level = per_student_expenditure.melt_data().get_school_level(selected_school_level)
        
        if individual_or_all == 'School Level':
                
            try:
        
                school_level_per_student_expenditure_by_year = per_student_expenditure_school_level.filter_by_multiple_columns({'Year': int(selected_year)})
                            
                chart = plot_stacked_bar_chart(school_level_per_student_expenditure_by_year,'School_Name','Expenditure', str(selected_year), selected_school_level, 'Spending Type')
                # Display the chart in Streamlit
                st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.warning(f"Per Pupil Expenditure Data Not Available for {selected_year}")

        elif individual_or_all == 'Individual School':

            try:
                individual_school_per_student_expenditure_by_year = per_student_expenditure_school_level.filter_by_multiple_columns({'School_Name': selected_school})
                individual_school_per_student_expenditure_by_year = individual_school_per_student_expenditure_by_year[individual_school_per_student_expenditure_by_year['Spending Type'].isin(['Federal Amount', 'State/Local Amount'])]
                chart = line_chart(individual_school_per_student_expenditure_by_year,'Expenditure', 'Spending Type', demo_category=None, selected_school = selected_school)
                # Display the chart in Streamlit
                st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.warning(f"Per Pupil Expenditure Data Not Available for {selected_school}")                    
                
    
    st.markdown("---")

with section5_container:
    st.markdown("**SECTION 5: Class Size**")
    st.write("The section below allows you to explore the class size for a selected school and year. "
            "You can select the school level and the year to view the class size for that school level.")
    class_size_display = DataDashboard("Click this Section to Explore Class Size",
                                       [f" Class Size by School Level or for an Individual School"], [2])
    with class_size_display.open_expander():

        column_group = class_size_display.render_columns()

        individual_or_all = st.radio('Select Option:', ['School Level', 'Individual School'], horizontal=True, key = 10)

        try:
        
            if individual_or_all == 'School Level':
                select_class_size_metric = st.radio("Select Class Size Metric:", options =['Avg_Class_Size', 'Math_Class_Size', 'ELA_Class_Size'], horizontal=True, key=11)
                filtered_class_size_df = class_size.melt_data().filter_by_multiple_columns({'Year': int(selected_year), 'School_Level': selected_school_level, 'Category': select_class_size_metric}).dropna().reset_index(drop=True)
                chart = plot_bar_chart(filtered_class_size_df,'School_Name','Class_Size', str(selected_year), selected_school_level)
            elif individual_or_all == 'Individual School':
                filtered_class_size_df = class_size.melt_data().filter_by_multiple_columns({'School_Level': selected_school_level, 'School_Name': selected_school}).dropna().reset_index(drop=True)
                chart = line_chart(filtered_class_size_df,'Class_Size', 'Category',demo_category=None, selected_school = selected_school)
                
                        # Display the chart in Streamlit
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.warning(f"No class size data available for {selected_school}.")