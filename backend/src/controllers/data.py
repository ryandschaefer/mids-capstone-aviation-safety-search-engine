from datasets import load_dataset

# Load HuggingFace dataset
ds = load_dataset("elihoole/asrs-aviation-reports")

def get_test_data():
    # Convert dataset to data frame
    df = ds["train"].to_pandas()
    # Return the top 15 records
    return df[:15].to_dict(orient = "records")