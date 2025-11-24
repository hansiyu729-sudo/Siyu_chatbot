import customtkinter as ctk
import pandas as pd
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 
EXCEL_FILENAME = "Test123.xlsx"
EXCEL_FILE_PATH = os.path.join(SCRIPT_DIR, EXCEL_FILENAME)


KEY_COLUMN_HEADER = "Svc (Service)" 
CLEANED_KEY_COLUMN = "cleaned_svc_key" 


KEYWORD_TO_COLUMN_MAP = {
    "first bus": "First Bus",
    "last bus": "Last Bus",
    "month": "Month",         
    "year": "Year",           
    

    "average loading": "Average Loading",
    "avg load": "Average Loading",
    "avg util": "Average Loading",
    

    "max loading": "Max Loading",      
    "max load": "Max Loading",         
    "max util": "Max Loading",         
    "max utilization": "Max Loading",  
    

    "min loading": "Min Loading",     
    "min load": "Min Loading",         
    "min util": "Min Loading",         
    "min utilization": "Min Loading",  
    

    "reliability": "Reliability",
    "reliable": "Reliability",
    "schedule adherence": "Reliability",
    "sch adh": "Reliability",
    
    "day type": "Day_Type",           
    "period": "Period"                
}

MONTH_NAME_TO_INT = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}

INT_TO_MONTH_NAME = {v: k.capitalize() for k, v in MONTH_NAME_TO_INT.items() if len(k) > 3}

DAY_TYPE_KEYWORD_TO_FILTER = {
    "weekend": ["Saturday", "Sunday/PH"],
    "public holiday": ["Sunday/PH"], 
    "ph": ["Sunday/PH"],
    "sat": ["Saturday"],
    "sun": ["Sunday/PH"],
    "saturday": ["Saturday"],
    "sunday": ["Sunday/PH"],
    "weekday": ["Weekday"],
    "wkd": ["Weekday"],
    "mon-fri": ["Weekday"]
}

DAY_TYPE_DISPLAY_NAMES = {
    "saturday": "Saturday",
    "sunday/ph": "Sunday/PH",
    "weekday": "Weekday"
}

PERIOD_MAPPING_PATTERNS = [
    (r'am.*(ext|extended)|(ext|extended).*am', "EA"), 
    (r'pm.*(ext|extended)|(ext|extended).*pm', "EP"), 
    (r'am.*(off|off\s*peak)|(off|off\s*peak).*am', "AO"), 
    (r'pm.*(off|off\s*peak)|(off|off\s*peak).*pm', "PO"), 
    (r'(full\s*day)|(normal|weekend)\s*day', "FA"), 
    (r'(full\s*night)|(normal|weekend)\s*night', "FP"), 
    (r'am', "AM"), 
    (r'pm', "PM"), 
]

PERIOD_DISPLAY_NAMES_REVERSE = {
    "AM": "AM Peak (2hr/Normal)",
    "EA": "AM Extended Peak",
    "AO": "AM Off Peak", 
    "PM": "PM Peak (2hr/Normal)",
    "EP": "PM Extended Peak",
    "PO": "PM Off Peak", 
    "FA": "Full Day",
    "FP": "Full Night",
}


FONT_SIZE = 16 

def _clean_dataframe_for_lookup(df: pd.DataFrame) -> pd.DataFrame:
    df[CLEANED_KEY_COLUMN] = df[KEY_COLUMN_HEADER].astype(str).str.lower().str.strip()
    return df

def _get_target_column(query_tokens: list) -> tuple[str | None, str | None]:
    query_text = " ".join(query_tokens)   
    for keyword, col_name in KEYWORD_TO_COLUMN_MAP.items():
        # Check if the keyword is present in the query text
        if keyword in query_text:
            if col_name in ["Average Loading", "Reliability"]:
                return col_name, "average" 
            elif col_name == "Max Loading":
                return col_name, "max" # Use 'max' aggregation
            elif col_name == "Min Loading":
                return col_name, "min" # Use 'min' aggregation
            elif "bus" in keyword:
                return col_name, "lookup" 
    return None, None

def _get_filters(query_tokens: list) -> dict:
    filters = {
        "month": None,
        "year": None,
        "day_type_keyword": None, 
        "period_code": None      
    }
    
    query_text = " ".join(query_tokens).lower()
    
    for token in query_tokens:
        token_lower = token.lower()
        if token_lower in MONTH_NAME_TO_INT:
            filters["month"] = MONTH_NAME_TO_INT[token_lower]
        try:
            year = int(token)
            if 2000 <= year <= 2100:
                filters["year"] = year
        except ValueError:
            pass

    day_type_keywords = list(DAY_TYPE_KEYWORD_TO_FILTER.keys())
    day_type_keywords.sort(key=len, reverse=True) 
    
    for keyword in day_type_keywords:
        if keyword in query_text:
            filters["day_type_keyword"] = keyword
            break

    for pattern, excel_code in PERIOD_MAPPING_PATTERNS:
        if re.search(pattern, query_text):
            filters["period_code"] = excel_code
            break

    return filters

def _calculate_metric(df_filtered: pd.DataFrame, target_col: str, agg_type: str) -> str | float:
    if df_filtered.empty:
        return "N/A"
        
    if agg_type == "lookup":
        return str(df_filtered.iloc[0][target_col])
        
    elif agg_type == "average":
        try:
            return df_filtered[target_col].mean()
        except TypeError:
            return f"Error: Data not numeric for averaging {target_col}"
            
    elif agg_type == "max":
        try:
            return df_filtered[target_col].max()
        except TypeError:
            return "Error: Data not numeric for finding max"
            
    elif agg_type == "min":
        try:
            return df_filtered[target_col].min()
        except TypeError:
            return "Error: Data not numeric for finding min"

    return "N/A"

def format_result_string(value: str | float, cleaned_value_field: str, month_int: int | None, year_int: int | None, day_type_str: str | None, period_code: str | None) -> str:  
    result = str(value) 
    if cleaned_value_field in ['average loading', 'max loading', 'min loading', 'reliability']: 
        try:
            numeric_value = float(value)
            percent_value = numeric_value * 100
            result = f"{percent_value:.1f}%"
        except (ValueError, TypeError):
            pass 

    context_parts = []
    
    month_name = INT_TO_MONTH_NAME.get(month_int)
    if month_name and year_int is not None:
        context_parts.append(f"{month_name} {year_int}")
    elif month_name:
        context_parts.append(month_name)
    elif year_int is not None:
        context_parts.append(str(year_int))
    
    if day_type_str:
        display_day_type = DAY_TYPE_DISPLAY_NAMES.get(day_type_str.lower(), day_type_str)
        context_parts.append(display_day_type)
        
    period_display = PERIOD_DISPLAY_NAMES_REVERSE.get(period_code)
    if period_display:
        context_parts.append(period_display)

    context_string = ""
    if context_parts:
        context_string = " (" + ", ".join(context_parts) + ")"
    
    return f"The **{cleaned_value_field}** is **{result}**{context_string}"

def get_bus_data(df: pd.DataFrame, service_key: str, target_col: str, agg_type: str, filters: dict) -> list[str]:

    df_service = df[df[CLEANED_KEY_COLUMN] == service_key]    
    if df_service.empty:
        return [f"Error: Service **{service_key.upper()}** not found in data."]

    user_day_type_keyword = filters.get("day_type_keyword")
    day_type_filters = DAY_TYPE_KEYWORD_TO_FILTER.get(user_day_type_keyword.lower() if user_day_type_keyword else None, [None])    
    results = []
    
    for internal_day_type in day_type_filters:
        df_filtered = df_service.copy()
        if filters["month"] is not None:
            df_filtered = df_filtered[df_filtered["Month"] == filters["month"]]
            
        if filters["year"] is not None:
            df_filtered = df_filtered[df_filtered["Year"] == filters["year"]]
            
        if internal_day_type is not None:
            day_type_col = KEYWORD_TO_COLUMN_MAP["day type"]
            df_filtered = df_filtered[df_filtered[day_type_col].astype(str).str.strip() == internal_day_type]
            
        period_code = filters["period_code"]
        if period_code is not None:
            period_col = KEYWORD_TO_COLUMN_MAP["period"]
            df_filtered = df_filtered[df_filtered[period_col].astype(str).str.strip().str.upper() == period_code]

        if df_filtered.empty:
            context_day_type = DAY_TYPE_DISPLAY_NAMES.get(internal_day_type.lower() if internal_day_type else 'all', 'All Days')
            if user_day_type_keyword in ["weekend", "public holiday", "ph"]:
                 results.append(f"No data found for Day Type: **{context_day_type}**.")
            else:
                 results.append(f"No data found for Service **{service_key.upper()}** under the selected criteria.")
            continue

        calculated_value = _calculate_metric(df_filtered, target_col, agg_type)
        
        formatted_string = format_result_string(
            calculated_value,
            target_col.lower(),
            filters["month"],
            filters["year"],
            internal_day_type, 
            period_code
        )
        results.append(formatted_string)
        
    return results


def process_query(df: pd.DataFrame, query: str) -> str:
    query_tokens = re.findall(r'\b\w+\b', query.lower())
    query_text = " ".join(query_tokens)
    service_key_match = re.search(r'(?:svc|service|bus)\s*(\w+)|(\b\d+[a-zA-Z]*\b|\b[a-zA-Z]+\d+\b)', query_text)
    bus_service = None
    if service_key_match:
        bus_service_raw = next((g for g in service_key_match.groups() if g), None)
        if bus_service_raw:
            bus_service = re.sub(r'[.,;\'"]+$', '', bus_service_raw).strip()
            
    if bus_service is None:
        return "Error: Please specify a bus service number or name (e.g., '10', '190', 'A1')."

    target_col, agg_type = _get_target_column(query_tokens)
    if target_col is None:
        return "Error: Please specify a metric to look up (e.g., 'First Bus', 'Last Bus', 'Average Loading', 'Max Load', 'Min Load', 'Reliability')."

    filters = _get_filters(query_tokens)
    result_list = get_bus_data(df, bus_service.lower(), target_col, agg_type, filters)
    final_output = [f"Results for Service **{bus_service.upper()}**:"] + result_list
    
    return "\n".join(final_output)

class ChatbotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("SG BUS - AI Chatbot")
        self.geometry("700x550")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.master_data_df = None
        self.master_data_status, self.master_data_df = self.load_excel_data(EXCEL_FILE_PATH)
        self.cleaned_keywords = {k.lower(): v for k, v in KEYWORD_TO_COLUMN_MAP.items()} 
        self.chat_font = ctk.CTkFont(family="Segoe UI", size=FONT_SIZE)
        self.chat_history = ctk.CTkTextbox(self, state="disabled", wrap="word", font=self.chat_font)
        self.chat_history.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        self.chat_history.tag_config("user_msg", foreground="black")
        self.chat_history.tag_config("bot_msg", foreground="blue")
        self.chat_history.tag_config("system_msg", foreground="red")    
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.user_input = ctk.CTkEntry(self.input_frame, 
                                       placeholder_text="Ask about a bus service (e.g., 'sch adh for svc 10 weekday')",
                                       font=self.chat_font)
        self.user_input.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="ew")
        self.user_input.bind("<Return>", self.process_input_event)
        self.send_button = ctk.CTkButton(self.input_frame, text="Send", command=self.process_input_event)
        self.send_button.grid(row=0, column=1, padx=(0, 0), pady=10, sticky="e")
        self.display_message("System", self.master_data_status, "system_msg")
        
    def load_excel_data(self, file_path):
        if not os.path.exists(file_path):
            return f"Error: Excel file not found at path: {file_path}. Using mock data.", self.create_mock_data()
            
        try:
            df = pd.read_excel(file_path, sheet_name=0) 
            df = _clean_dataframe_for_lookup(df)
            return "Hello, feel free to start. :)", df

        except Exception as e:
            return f"Failed to load Excel file: {e}. Using mock data.", self.create_mock_data()

    def create_mock_data(self):
        mock_df = pd.DataFrame({
            KEY_COLUMN_HEADER: ["10", "10", "10", "10", "20", "20", "20", "20", "166", "166"],
            "Month": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            "Year": [2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024],
            "Day_Type": ["Weekday", "Saturday", "Sunday/PH", "Weekday", "Saturday", "Sunday/PH", "Weekday", "Saturday", "Saturday", "Sunday/PH"],
            "Period": ["AM", "OA", "OA", "PM", "OP", "OP", "EA", "EP", "OA", "OA"],
            "First Bus": ["05:30", "06:00", "07:15", "05:45", "06:30", "07:00", "08:15", "08:45", "07:00", "08:00"],
            "Last Bus": ["23:30", "23:00", "22:45", "00:00", "23:15", "22:50", "23:00", "22:45", "23:00", "22:30"],
            "Average Loading": [0.65, 0.40, 0.25, 0.70, 0.50, 0.35, 0.60, 0.45, 0.30, 0.20],
            "Max Loading": [0.85, 0.55, 0.40, 0.90, 0.75, 0.50, 0.80, 0.60, 0.45, 0.35],
            "Min Loading": [0.45, 0.15, 0.05, 0.50, 0.20, 0.10, 0.40, 0.25, 0.10, 0.05],
            "Reliability": [0.92, 0.95, 0.88, 0.91, 0.85, 0.87, 0.94, 0.90, 0.89, 0.93]
        })
        return _clean_dataframe_for_lookup(mock_df)

    def display_message(self, sender, message, tag):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", f"{sender}: ", tag)
        self.chat_history.insert("end", f"{message}\n\n", "normal")
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def process_input_event(self, event=None):
        user_query = self.user_input.get().strip()
        self.user_input.delete(0, 'end')
        
        if not user_query:
            return

        self.display_message("You", user_query, "user_msg")
        
        if self.master_data_df is None:
             response = "System Error: The master data could not be loaded. Please check the `EXCEL_FILE_PATH`."
        else:
             response = process_query(self.master_data_df, user_query)
            
        self.display_message("Bot", response, "bot_msg")


if __name__ == "__main__":
    ctk.set_appearance_mode("System") 
    ctk.set_default_color_theme("blue") 
    
    app = ChatbotApp()
    app.mainloop()
