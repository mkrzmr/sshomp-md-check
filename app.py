# app.py
from flask import Flask, render_template, request, send_file
import requests
from io import BytesIO

app = Flask(__name__)


# Function to check placeholder descriptions
def is_valid_description(description):
    placeholders = ["no description provided", "No description provided"]
    return description and description.strip() not in placeholders

# Function to validate and score the metadata per category
def validate_metadata(json_data, item_type):
    # Initialize categories
    results = {
        "Generic Metadata": {},
        "Categorisation Metadata": {},
        "Context Metadata": {},
        "Access Metadata": {},
        "Bibliographic metadata": {},
        "Technical Metadata": {}
    }
    suggestions = []

    # Extract the `properties` array for Categorisation Metadata
    properties = json_data.get("properties", [])

    # Define the fields for each item type
    metadata_fields = {
        "tools-services": {
            "Generic Metadata": ["label", "description", "contributors", "accessibleAt", "externalIds", "media", "thumbnail", "relatedItems"],
            "Categorisation Metadata": ["activity", "keyword", "discipline", "language", "intended-audience", "resource-category"],
            "Context Metadata": ["see-also"],
            "Access Metadata": ["license"],
            "Technical Metadata": ["technology-readiness-level", "version"]
        },
        "training-materials": {
            "Generic Metadata": ["label", "description", "contributors", "accessibleAt", "externalIds", "media", "thumbnail", "relatedItems"],
            "Categorisation Metadata": ["activity", "keyword", "discipline", "language", "intended-audience", "resource-category"],
            "Context Metadata": ["see-also"],
            "Access Metadata": ["license"],
            "Technical Metadata": []
        },
        "publications": {
            "Generic Metadata": ["label", "description", "contributors", "accessibleAt", "externalIds", "media", "thumbnail", "relatedItems"],
            "Categorisation Metadata": ["activity", "keyword", "discipline", "language", "resource-category"],
            "Context Metadata": ["see-also"],
            "Access Metadata": ["license"],
            "Bibliographic metadata": ["publication-type", "publisher", "publication-place", "year", "journal", "conference", "volume", "issue", "pages"]
        },
        "datasets": {
            "Generic Metadata": ["label", "description", "contributors", "accessibleAt", "externalIds", "media", "thumbnail", "relatedItems"],
            "Categorisation Metadata": ["activity", "keyword", "discipline", "language", "resource-category"],
            "Context Metadata": ["see-also"],
            "Access Metadata": ["license"],
            "Bibliographic metadata": ["publisher", "year"]
        },
        "workflows": {
            "Generic Metadata": ["label", "description", "contributors", "externalIds", "media", "thumbnail", "relatedItems"],
            "Categorisation Metadata": ["activity", "keyword", "discipline", "language", "standard", "resource-category"],
            "Context Metadata": ["see-also"],
            "Access Metadata": ["license"],
            "Technical Metadata": []
        }
    }

# Helper function to check a field in the `properties` array
    def check_property(field_code):
        return any(prop['type']['code'] == field_code for prop in properties)

    # Validate Generic Metadata (directly from JSON)
    for category, fields in metadata_fields[item_type].items():
        if category in ("Categorisation Metadata", "Context Metadata", "Access Metadata", "Technical Metadata", "Bibliographic metadata") :
            for field in fields:
                # For Categorisation Metadata, check the nested properties
                results[category][field] = check_property(field)
                if not results[category][field]:
                    suggestions.append(f"Add or update the '{field}' field in {category}.")
        else:
            # Other metadata categories (Generic)
            results[category] = {}
            for field in fields:
                results[category][field] = bool(json_data.get(field))
                if not results[category][field]:
                    suggestions.append(f"Add or update the '{field}' field in {category}.")

    # Calculate overall score
    total_fields = sum(len(fields) for fields in metadata_fields[item_type].values())
    filled_fields = sum(sum(value for value in fields.values()) for fields in results.values())
    overall_score = int((filled_fields / total_fields) * 100)

    return json_data.get("label"), results, suggestions, {}, overall_score



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        persID = request.form['persID']
        item_type = request.form['itemType']  # Get the selected item type

        if persID and item_type:
            # Adjust the API endpoint based on the item type
            api_url = f"http://marketplace-api.sshopencloud.eu/api/{item_type}/{{}}".format(persID)

            # Call the external API to get the metadata
            response = requests.get(api_url)
            if response.status_code == 200:
                json_data = response.json()
                # Validate the received JSON data and calculate score
                tool_name, results, suggestions, category_scores, overall_score = validate_metadata(json_data, item_type)
                return render_template('result.html', tool_name=tool_name, results=results, suggestions=suggestions, category_scores=category_scores, overall_score=overall_score)
            else:
                return render_template('error.html', message=f"API request failed with status code {api_url, response.status_code, response.headers}")
        else:
            return render_template('error.html', message="persID and item type are required")

    return render_template('index.html')


@app.route('/export', methods=['POST'])
def export_results():
    tool_name = request.form['tool_name']
    results = request.form['results']
    suggestions = request.form['suggestions']
    overall_score = request.form['overall_score']

    # Prepare the text content
    text_content = f"Metadata Validation Results for {tool_name}\n\n"
    text_content += f"Overall Metadata Score: {overall_score}%\n\n"
    text_content += "Detailed Results:\n"
    for category, fields in eval(results).items():
        text_content += f"\n{category}:\n"
        for field, status in fields.items():
            status_text = 'Available' if status else 'Missing'
            text_content += f"- {field}: {status_text}\n"
    
    text_content += "\nSuggested Actions:\n"
    for suggestion in eval(suggestions):
        text_content += f"- {suggestion}\n"

    # Export as .txt file
    buffer = BytesIO()
    buffer.write(text_content.encode('utf-8'))
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"{tool_name}_metadata_validation.txt", mimetype="text/plain")

if __name__ == '__main__':
    app.run(debug=True)

