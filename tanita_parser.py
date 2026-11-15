from datetime import datetime
from tabulate import tabulate
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Directory containing the measurement files
LINE_SEPARATOR= "\n"
ITEM_SEPARATOR = ","
DATE_KEY = "DT"
TIME_KEY = "Ti"
DATE_TIME_KEY = "datetime"

# Mapping of Tanita headers to meaningful names
HEADER_MAPPING = {
    "{0": ["Unknown_16", "Unknown_16"],
    "~0": ["Length unit", "Unidade de Comprimento"] ,
    "~1": ["Mass unit",  "Unidade de Massa"],
    "~2": ["Unknown_4", "Unknown_4"],
    "~3": ["Unknown_3", "Unknown_3"],
    "Bt": ["Athlete mode", "Modo Atleta"],
    "Wk": ["Body_mass [kg]", "Massa Coporal [Kg]"],
    "MI": ["BMI [Kg/m2]", "IMC [Kg/m2]"],
    "MO": ["Model","Modelo"],
    "DT": ["Measurement Date","Data de Medição"],
    "Ti": ["Measurement Time","Hora de Medição"],
    "GE": ["Gender", "Genero Biologico"],
    "AG": ["Age", "Idade"],
    "Hm": ["Height [cm]", "Altura [cm]"],
    "AL": ["Activity Level", "Nivel de Atividade"],
    "FW": ["Global Fat [%]", "Gordura Total [%]"],
    "Fr": ["Right Arm Fat [%]", "Gordura Braco direito [%]"],
    "Fl": ["Left Arm Fat [%]", "Gordura braco Esquerdo [%]"],
    "FR": ["Right Leg Fat [%]", "Gordura Perna Direita [%]"],
    "FL": ["Left Leg Fat [%]", "Gordura Perna Esquerda [%]"],
    "FT": ["Torso Fat [%]", "Gordura Torso [%]"],
    # The muscle values are masses in kg. The five segments add up to the total.
    "mW": ["Global Muscle [kg]", "Musculo Total [kg]"],
    "mr": ["Right Arm Muscle [kg]", "Musculo Braco Direito [kg]"],
    "ml": ["Left Arm Muscle [kg]", "Musculo Braco Esquerdo [kg]"],
    "mR": ["Right Leg Muscle [kg]", "Musculo Perna Direita [kg]"],
    "mL": ["Left Leg Muscle [kg]", "Musculo Perna Esquerda [kg]"],
    "mT": ["Torso Muscle [kg]", "Musculo Torso [kg]"],
    "bW": ["Estimated_bone_mass [Kg]", "Massa Ossea [Kg]"],
    "IF": ["Visceral_fat_rating", "Grau de Gordura Visceral"],
    "rA": ["Metabolic_age", "Idade Metabolica"],
    "rD": ["Daily_calorie_intake [Kcal]", "Calorias Diarias [Kcal]"],
    "ww": ["Global Body Water [%]", "Água Corporal Total [%]"],
    "CS": ["Unknown_BC", "Unknown_BC"],
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


def build_datetime_list(parsed_dictionary):
    # Build the datetime list one time, after all lines are parsed.
    dates = parsed_dictionary.get(DATE_KEY, [])
    times = parsed_dictionary.get(TIME_KEY, [])
    parsed_dictionary[DATE_TIME_KEY] = [
        parse_date_time(date_str, time_str)
        for date_str, time_str in zip(dates, times)
    ]


def sort_by_datetime(parsed_dictionary):
    # Put the measurements in time order. The report uses the last rows.
    datetime_list = parsed_dictionary[DATE_TIME_KEY]
    order = sorted(range(len(datetime_list)), key=lambda index: datetime_list[index])
    for key, values in parsed_dictionary.items():
        if len(values) == len(order):
            parsed_dictionary[key] = [values[index] for index in order]


def parse_tanita_csv(file):
    parsed_dictionary = {}

    content = file.read()
    content_list = content.split(LINE_SEPARATOR)

    for line in content_list:
        if not line.strip():
            continue
        line_list = line.split(ITEM_SEPARATOR)
        parse_line(line_list, parsed_dictionary)

    build_datetime_list(parsed_dictionary)
    sort_by_datetime(parsed_dictionary)
    return parsed_dictionary


def load_csv(path):
    # Read and parse one Tanita CSV file.
    with open(path, "r", encoding="utf-8") as file:
        return parse_tanita_csv(file)


def print_most_recent_info(data_dict, header_mapping):
    # Prepare the table data
    table_data = []
    
    for key, value in data_dict.items():
        # Skip the 'datetime' key for this mapping
        if key == 'datetime':
            continue
        
        # Get the readable label from the header_mapping
        label = header_mapping.get(key, key)[1]
        
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
    labels = [header_mapping.get(key, key)[1] for key in relevant_keys]
    
    # Create a new figure
    
    
    # Plot each relevant metric
    for idx, key in enumerate(relevant_keys):
        plt.figure(figsize=(10, 6))
        y_values = data_dict[key]  # Get the values for the current key
        plt.plot(datetime_values, y_values, label=labels[idx])
    
        # Formatting the plot
        plt.title(f"{labels[idx]}")
        plt.xlabel('Date and Time')
        plt.ylabel('Values')

        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

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
