from datetime import datetime
from tabulate import tabulate
import re
import matplotlib.pyplot as plt

# Directory containing the measurement files
LINE_SEPARATOR= "\n"
ITEM_SEPARATOR = ","
DATE_KEY = "DT"
TIME_KEY = "Ti"
DATE_TIME_KEY = "datetime"

# Mapping of Tanita headers to meaningful names
HEADER_MAPPING = {
    "{0": "Unknown_16", 
    "~0": "Length unit", 
    "~1": "Mass unit", 
    "~2": "Unknown_4",
    "~3": "Unknown_3",
    "Bt": "Athlete mode",
    "Wk": "Body_mass [kg]",
    "MI": "BMI [Kg/m2]",
    "MO": "Model",
    "DT": "Measurement Date",
    "Ti": "Measurement Time",
    "GE": "Gender",
    "AG": "Age",
    "Hm": "Height",
    "AL": "Activity Level",
    "FW": "Global Fat pct [%]",
    "Fr": "Right Arm Fat [%]",
    "Fl": "Left Arm Fat [%]",
    "FR": "Right Leg Fat [%]",
    "FL": "Left Leg Fat [%]",
    "FT": "Torso Fat[%]",
    "mW": "Global Muscle [%]",
    "mr": "Right Arm Muscle [%]",
    "ml": "Left Arm Muscle [%]",
    "mR": "Right Leg Muscle [%]",
    "mL": "Left Leg Muscle [%]",
    "mT": "Torso Muscle [%]",
    "bW": "Estimated_bone_mass [Kg]",
    "IF": "Visceral_fat_rating",
    "rA": "Metabolic_age",
    "rD": "Daily_calorie_intake [Kcal]",
    "ww": "Global_body_water_pct [%]",
    "CS": "Unknown_BC"
}

def parse_number(item):
    return float(item)

def parse_default(item):
    # return item
    ret = re.sub(r"['\"]", "", item)
    return ret


def parse_date_time(date_str, time_str):
    # Combine the date and time strings into one
    combined_str = date_str + ' ' + time_str
    # Define the format for parsing (including seconds)
    date_time_format = "%d/%m/%Y %H:%M:%S"
    # Parse the combined string into a datetime object
    return datetime.strptime(combined_str, date_time_format)

PARSE_MAP = {
    "{0": parse_default,  # Unknown_16, leaving it as default because it seems unclear
    "~0": parse_default,  # Length_unit, leaving it as default (if it's a string or unit)
    "~1": parse_default,  # Mass_unit, leaving it as default (if it's a string or unit)
    "~2": parse_default,  # Unknown_4, leaving it as default
    "~3": parse_default,  # Unknown_3, leaving it as default
    "Bt": parse_default,  # Athlete_mode, leaving as default (could be a boolean or string)
    "Wk": parse_number,   # Body_mass, parsing as number (float)
    "MI": parse_number,   # BMI, parsing as number (float)
    "MO": parse_default,  # Model, leaving as default (likely a string)
    "DT": parse_default,  # Measurement_Date, parsing as date
    "Ti": parse_default,  # Measurement_Time, parsing as date
    "GE": parse_default,  # Gender, leaving as default (likely a string)
    "AG": parse_number,   # Age, parsing as number (int)
    "Hm": parse_number,   # Height, parsing as number (float or int)
    "AL": parse_default,  # Activity_Level, leaving as default (could be a string or level code)
    "FW": parse_number,   # Global_fat_pct, parsing as number (float)
    "Fr": parse_number,   # Arm_fat_right_pct, parsing as number (float)
    "Fl": parse_number,   # Arm_fat_left_pct, parsing as number (float)
    "FR": parse_number,   # Leg_fat_right_pct, parsing as number (float)
    "FL": parse_number,   # Leg_fat_left_pct, parsing as number (float)
    "FT": parse_number,   # Torso_fat_pct, parsing as number (float)
    "mW": parse_number,   # Global_muscle_pct, parsing as number (float)
    "mr": parse_number,   # Arm_muscle_right_pct, parsing as number (float)
    "ml": parse_number,   # Arm_muscle_left_pct, parsing as number (float)
    "mR": parse_number,   # Leg_muscle_right_pct, parsing as number (float)
    "mL": parse_number,   # Leg_muscle_left_pct, parsing as number (float)
    "mT": parse_number,   # Torso_muscle_pct, parsing as number (float)
    "bW": parse_number,   # Estimated_bone_mass, parsing as number (float)
    "IF": parse_number,   # Visceral_fat_rating, parsing as number (float or int)
    "rA": parse_number,   # Metabolic_age, parsing as number (int)
    "rD": parse_number,   # Daily_calorie_intake, parsing as number (float or int)
    "ww": parse_number,   # Global_body_water_pct, parsing as number (float)
    "CS": parse_default    # Unknown_BC, leaving as default (seems unclear)
}



def parse_line(line_list, parsed_dictionary):
    current_key = None
    for item in line_list:
        if current_key == None:
            current_key = item
            continue
        
        if current_key not in parsed_dictionary:
            parsed_dictionary[current_key] = []
    
        parser = PARSE_MAP[current_key]
        data = parser(item)
        parsed_dictionary[current_key].append(data)
        current_key = None
    
    parsed_dictionary[DATE_TIME_KEY] = []
    for i in range(len(parsed_dictionary[DATE_KEY])):
        date_str =  parsed_dictionary[DATE_KEY][i]
        time_str = parsed_dictionary[TIME_KEY][i]
        datetime_info = parse_date_time(date_str,time_str)
        parsed_dictionary[DATE_TIME_KEY].append(datetime_info)

            

def parse_tanita_csv(file):
    parsed_dictionary = {}

    content = file.read()
    content_list = content.split(LINE_SEPARATOR)[:-1]

    for line in content_list:
        line_list = line.split(ITEM_SEPARATOR)
        parse_line(line_list,parsed_dictionary)
    
    return parsed_dictionary


def print_most_recent_info(data_dict, header_mapping):
    # Prepare the table data
    table_data = []
    
    for key, value in data_dict.items():
        # Skip the 'datetime' key for this mapping
        if key == 'datetime':
            continue
        
        # Get the readable label from the header_mapping
        label = header_mapping.get(key, key)
        
        # Get the most recent value (the last one in the list)
        most_recent_value = value[-1]
        
        # Append the row for the table
        table_data.append([label, most_recent_value])

    # Adding datetime to the table
    table_data.append(['Datetime', data_dict['datetime'][-1]])

    # Print the table using tabulate for better formatting
    print(tabulate(table_data, headers=['Label', 'Most Recent Value'], tablefmt='grid'))

def print_table(data_dict):
    print_most_recent_info(data_dict, HEADER_MAPPING)

def plot_relevant_data(data_dict, header_mapping):
    # Extract the datetime values (used as x-axis)
    datetime_values = data_dict['datetime']
    
    # Define the relevant data to plot (for example: Body_mass, BMI, Height, Age)
    # relevant_keys = ['Wk', 'MI', 'Hm', 'AG']  # You can add other keys here
    relevant_keys = [
    'Wk', 'FW', 'Fr', 'Fl', 'FR', 'FL', 'FT', 'mr', 'ml', 'mR', 'mL', 
    'mT', 'IF', 'rD', 'ww'
    ]
    labels = [header_mapping.get(key, key) for key in relevant_keys]
    
    # Create a new figure
    
    
    # Plot each relevant metric
    for idx, key in enumerate(relevant_keys):
        plt.figure(figsize=(10, 6))
        y_values = data_dict[key]  # Get the values for the current key
        plt.plot(datetime_values, y_values, label=labels[idx])
    
        # Formatting the plot
        plt.title('Relevant Data Over Time')
        plt.xlabel('Date and Time')
        plt.ylabel('Values')
        plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
        plt.legend(loc='upper left')
        # Display the plot
        plt.tight_layout()
        plt.show()

def plot_data(data_dict):
    plot_relevant_data(data_dict, HEADER_MAPPING)


def main():
    DATA_DIR = "DATA1.CSV"
    with open(DATA_DIR, "r") as file:
        data= parse_tanita_csv(file)
    print(data)
    print_table(data)


if __name__ == "__main__":
    main()
