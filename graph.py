import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import pdf_handler
import re
from client import model  

def initialize_mindmap(base_context, json_save_path):
    """Initialize mind map based on the selected PDF using Gemini"""
    # if not st.session_state.get('selected_pdf'):
    #     st.error("Please select a PDF first.")
    #     return None
    #
    # pdf_file = st.session_state.uploaded_pdfs[st.session_state.selected_pdf]
    # pdf_text = pdf_handler.extract_text_from_pdf(pdf_file)  # Assuming pdf_handler is defined
    #
    # if not pdf_text.strip():
    #     st.error("No text available in the selected PDF.")
    #     return None

    prompt = base_context + f"""

    Return the structure as JSON with:
    {{
        "nodes": [
            {{
                "id": "unique_id_1",
                "label": "Main Concept 1",
                "size": 2,
                "color": "#6a9df6",
                "description": "Detailed explanation..."
            }}
        ],
        "edges": [
            {{
                "source": "source_node_id",
                "target": "target_node_id",
                "relation": "relationship_type"
            }}
        ]
    }}
    Include 5-7 main nodes and 2-3 subnodes for each.
    Make the structure hierarchical and meaningful.
    Ensure all node labels are unique and don't contain special characters.
    """

    try:
        # Generate mind map structure using Gemini
        response = model.generate_content(prompt)
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        graph_data = json.loads(json_str)
        # Save the generated JSON to a file
        with open(json_save_path, 'w') as f:
            json.dump(graph_data, f, indent=4)

        # Create networkx graph
        G = nx.DiGraph()

        # Add nodes with attributes
        for node in graph_data['nodes']:
            label = node['label'].strip()
            G.add_node(
                label,
                size=node.get('size', 1) * 1500,
                color=node.get('color', '#6a9df6'),
                description=node.get('description', 'No description available')
            )

        # Add edges with relationships
        for edge in graph_data['edges']:
            source = next(n['label'].strip() for n in graph_data['nodes'] if n['id'] == edge['source'])
            target = next(n['label'].strip() for n in graph_data['nodes'] if n['id'] == edge['target'])
            if source in G and target in G:
                G.add_edge(source, target, relation=edge.get('relation', 'related'))

        # Use the first node label as the root if the original topic is not found
        root_node = list(G.nodes())[0] 

        st.session_state.mindmap = {
            'graph': G,
            'root': root_node,
            'initial_root': root_node,
            'current_focus': root_node,
            'visible_nodes': set(G.nodes()),
            'selected_node': None,
            'history': []
        }

        return G

    except Exception as e:
        st.error(f"Mind map creation failed: {str(e)}")
        return None

def get_subgraph(G, root_node):
    """Get subgraph starting from root_node with safety checks"""
    if root_node not in G:
        if not G.nodes():
            return G
        root_node = list(G.nodes())[0]

    nodes = set()
    nodes.add(root_node)

    try:
        for successor in nx.dfs_preorder_nodes(G, root_node):
            nodes.add(successor)
    except nx.NetworkXError:
        nodes.add(root_node)

    for predecessor in G.predecessors(root_node):
        nodes.add(predecessor)

    return G.subgraph(nodes)


def draw_interactive_mindmap():
    """Draw interactive mind map with navigation using Streamlit components"""
    if 'mindmap' not in st.session_state or not st.session_state.mindmap['graph']:
        return

    G = st.session_state.mindmap['graph']
    current_root = st.session_state.mindmap['current_focus']
    
    # Create subgraph based on current focus with safety checks
    try:
        subG = get_subgraph(G, current_root)
    except:
        subG = G
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='#f8f9fa')
    
    # Compute layout
    if subG.number_of_nodes() > 0:
        pos = nx.spring_layout(subG, k=1.5, iterations=100, seed=42)
    else:
        pos = {}

    # Draw edges
    edge_styles = {
        'contains': {'style': 'dashed', 'width': 2, 'color': '#6c757d'},
        'related': {'style': 'solid', 'width': 1.5, 'color': '#495057'},
        'influences': {'style': 'solid', 'width': 2, 'color': '#2b8a3e', 'alpha': 0.8}
    }
    
    for u, v, data in subG.edges(data=True):
        relation = data.get('relation', 'related')
        style = edge_styles.get(relation, edge_styles['related'])
        nx.draw_networkx_edges(
            subG, pos, edgelist=[(u, v)],
            width=style['width'],
            style=style['style'],
            edge_color=style['color'],
            alpha=style.get('alpha', 0.7),
            ax=ax,
            arrows=True,
            arrowstyle='-|>',
            arrowsize=15
        )
    
    # Draw nodes
    node_colors = []
    node_sizes = []
    for node in subG.nodes():
        if node == st.session_state.mindmap.get('selected_node'):
            node_colors.append('#ff9f1c')  # Selected
        elif node == current_root:
            node_colors.append('#2b8a3e')  # Current focus
        else:
            node_colors.append(subG.nodes[node].get('color', '#4dabf7'))  # Default
        
        node_sizes.append(subG.nodes[node].get('size', 1500))
    
    if subG.number_of_nodes() > 0:
        nx.draw_networkx_nodes(
            subG, pos, ax=ax,
            node_size=node_sizes,
            node_color=node_colors,
            edgecolors='#343a40',
            linewidths=1,
            alpha=0.9
        )
        
        # Draw labels
        nx.draw_networkx_labels(
            subG, pos, ax=ax,
            labels={n: n for n in subG.nodes()},
            font_size=10,
            font_weight='bold',
            font_family='sans-serif',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.3')
        )

    # Display the figure
    st.pyplot(fig, use_container_width=True)

    # Node information and navigation using Streamlit components
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.session_state.mindmap.get('selected_node'):
            node = st.session_state.mindmap['selected_node']
            desc = G.nodes[node].get('description', 'No description available')
            st.markdown(f"### {node}")
            st.markdown(desc)
        else:
            st.info("Click on a node in the graph to see details")
    
    with col2:
        if st.button("🔙 Back to parent", use_container_width=True):
            navigate_up()
        
        if st.button("🏠 Reset to root", use_container_width=True):
            navigate_reset()

    # Node selection using coordinates
    if subG.number_of_nodes() > 0:
        st.markdown("### Select Node")
        selected = st.selectbox(
            "Choose a node to focus on:",
            options=list(subG.nodes()),
            index=list(subG.nodes()).index(current_root) if current_root in subG.nodes() else 0,
            label_visibility="collapsed"
        )
        
        if selected != current_root:
            st.session_state.mindmap['history'].append(st.session_state.mindmap['current_focus'])
            st.session_state.mindmap['current_focus'] = selected
            st.session_state.mindmap['selected_node'] = selected
            st.rerun()

def navigate_up():
    """Navigate to parent node"""
    if 'mindmap' not in st.session_state:
        return
        
    G = st.session_state.mindmap['graph']
    current = st.session_state.mindmap['current_focus']
    predecessors = list(G.predecessors(current))
    
    if predecessors:
        st.session_state.mindmap['current_focus'] = predecessors[0]
    elif st.session_state.mindmap['history']:
        st.session_state.mindmap['current_focus'] = st.session_state.mindmap['history'].pop()
    
    st.session_state.mindmap['selected_node'] = None
    st.rerun()

def navigate_reset():
    """Reset view to initial root"""
    if 'mindmap' not in st.session_state:
        return
        
    st.session_state.mindmap['current_focus'] = st.session_state.mindmap['initial_root']
    st.session_state.mindmap['selected_node'] = None
    st.session_state.mindmap['history'] = []
    st.rerun()