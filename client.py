import google.generativeai as genai
import streamlit as st
import networkx as nx
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)

# Create model instance
model = genai.GenerativeModel("gemini-2.0-flash")

def generate_answer(question):
    """Generates an answer to a question using Google GenAI and returns the answer."""
    if not question.strip():
        return "No question provided."

    # Call generate_text from client.py
    answer = model.generate_content(contents=question).text
    return answer

def ask_question_on_notes(question, notes_text):
    """Sends a question and notes to Google GenAI and returns the answer."""
    if not notes_text.strip():
        return "No notes provided to answer the question."

    prompt = f"""Given the following notes, answer the question:

    Notes:
    {notes_text}

    Question:
    {question}
    """

    # Call generate_text from client.py
    answer = model.generate_content(contents=prompt).text  
    return answer

def generate_graph(prompt):
    """Generates a graph from a given prompt using Google GenAI and returns a networkx graph."""
    try:
        # Call Google GenAI model to generate content (expecting JSON for nodes and edges)
        response = model.generate_content(contents=prompt)
        mind_map_data = response.text

        # Usuń ewentualne znaczniki Markdown
        mind_map_data = mind_map_data.strip().removeprefix("```json").removesuffix("```").strip()

        if not mind_map_data:
            st.error("No mind map data returned.")  # Display error message in Streamlit
            return None  # Indicate failure by returning None

        # Try to parse the mind map data as JSON
        try:
            mind_map_json = json.loads(mind_map_data)
        except json.JSONDecodeError as e:
            st.error(f"Error parsing the mind map data as JSON: {e}")  # Display error message
            st.write(f"Raw response: {mind_map_data}")  # Show raw response for debugging
            return None  # Indicate failure

        # Create a NetworkX graph
        graph = nx.Graph()
        st.write("Graph created successfully.")  

        # Ensure the mind_map_json contains 'nodes' and 'edges' lists and they are lists
        if "nodes" in mind_map_json and isinstance(mind_map_json["nodes"], list) and \
           "edges" in mind_map_json and isinstance(mind_map_json["edges"], list):
            
            # Add nodes with error handling
            for node in mind_map_json["nodes"]:
                if isinstance(node, dict) and 'id' in node and 'label' in node:
                    graph.add_node(node['id'], label=node['label'])
                else:
                    st.warning(f"Skipping invalid node: {node}")  # Log warning for invalid node

            # Add edges with error handling
            for edge in mind_map_json["edges"]:
                if isinstance(edge, dict) and 'source' in edge and 'target' in edge:
                    graph.add_edge(edge['source'], edge['target'], relation=edge.get('label', 'related'))
                else:
                    st.warning(f"Skipping invalid edge: {edge}")  # Log warning for invalid edge

            return graph  # Return the networkx graph
        else:
            st.error("Invalid mind map structure: 'nodes' or 'edges' missing or not lists.")  # Display error message
            st.write(f"Raw response: {mind_map_data}")  # Show raw response for debugging
            return None  # Indicate failure

    except Exception as e:
        st.error(f"Error generating graph: {e}")  # Display error message
        return None  # Indicate failure