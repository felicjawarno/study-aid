import streamlit as st

import client
import pdf_handler
import graph
from client import model
from database import database_manager
import os
import shutil
import tempfile


def ask_question_on_notes(question, notes_text):
    response = model.generate_content(
        model="gemini-2.0-flash",
        contents=f"Given the following notes: {notes_text}\nAnswer the question: {question}",
    )
    return response.text

def main_app():
    # Session state initialization
    session_defaults = {
        'project': None,
        'username': "Guest",
        'uploaded_pdfs': {},
        'selected_pdf': None,
        'quiz_data': {
            'questions': [],
            'index': 0,
            'score': 0,
            'active': False,
            'show_answers': False,
            'answered': {}
        },
        'mindmap': {
            'graph': None,
            'root': None,
            'visible_nodes': set(),
            'current_focus': None
        }
    }

    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # App header
    st.title(f"📚 Study Assistant - {st.session_state.username}")
    
    # Sidebar
    with st.sidebar:
        # st.header("Account")
        # if st.button("Logout"):
        #     for key in list(st.session_state.keys()):
        #         del st.session_state[key]
        #     st.rerun()

        st.header("Project Manager")
        projects = database_manager.get_all_projects()
        project_names = [p[1] for p in projects]
        project_map = {p[1]: p for p in projects}

        mode = st.radio("Select mode", ["Select Existing", "Create New"])

        if mode == "Select Existing":
            if project_names:
                selected_name = st.selectbox("Choose a project", project_names)
                st.session_state.selected_project = project_map[selected_name]
                st.success(f"Selected project: {selected_name}")
            else:
                st.warning("No projects available. Create one below.")
                return None

        else:
            new_name = st.text_input("Project name")
            # new_path = st.text_input("Path to contents", value=os.getcwd())
            new_path = os.path.join(os.getcwd(), 'projects', new_name)
            if st.button("Create Project"):
                if new_name and new_path:
                    try:
                        database_manager.insert_project(new_name, new_path)
                        st.success(f"Project '{new_name}' created!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please provide both name and path.")

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Materials", "❓ Ask Question", "🗺️ Mind Map", "📝 Quiz"])

    with tab1:  # PDF Materials
        st.header("PDF Tools")

        if "selected_project" not in st.session_state or st.session_state.selected_project is None:
            st.warning("Please select a project from the sidebar.")
        else:
            project_id, project_name, project_path, _ = st.session_state.selected_project
            st.session_state.uploaded_pdfs = database_manager.get_all_documents(project_id)

            uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

            if uploaded_file:
                os.makedirs(project_path, exist_ok=True)
                save_path = os.path.join(project_path, "documents", uploaded_file.name)

                doc_id = database_manager.insert_document(project_id, uploaded_file.name, uploaded_file.name)

                if doc_id is not None:
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.session_state.uploaded_pdfs[uploaded_file.name] = doc_id
                    database_manager.parse_insert_document(project_id, doc_id)
            else:
                st.warning("No file uploaded yet.")

            selected_pdf = st.selectbox(
                "Select PDF",
                list(st.session_state.uploaded_pdfs.keys()),
                key="pdf_selector"
            )
            st.session_state.selected_pdf = selected_pdf

            if st.session_state.selected_pdf:
                pdf_path = os.path.join(project_path, "documents", selected_pdf)

                with st.expander("📄 PDF Preview", expanded=False):
                    try:
                        pdf_handler.display_pdf_preview(pdf_path)
                    except Exception as e:
                        st.error(f"Failed to display PDF: {str(e)}")

                if st.button("🗑️ Delete this PDF"):
                    try:
                        # --- Delete from filesystem ---
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)

                        database_manager.delete_document(st.session_state.uploaded_pdfs[st.session_state.selected_pdf])
                        st.success(f"Deleted {st.session_state.selected_pdf} from database and disk.")
                        # Optionally clear from session state
                        del st.session_state.uploaded_pdfs[st.session_state.selected_pdf]
                        st.session_state.selected_pdf = None
                        st.rerun()

                    except Exception as e:
                        st.error(f"Failed to delete PDF: {str(e)}")
                
                # with st.expander("💬 Ask Questions", expanded=False):
                #     question = st.text_input("Your question:")
                #     if question:
                #         with st.spinner("Analyzing content..."):
                #             try:
                #                 pdf_text = pdf_handler.extract_text_from_pdf(pdf_file)
                #                 response = model.generate_content(
                #                     f"Document excerpt: {pdf_text[:5000]}\nQuestion: {question}"
                #                 )
                #                 st.info(f"**Answer:** {response.text}")
                #             except Exception as e:
                #                 st.error(f"Failed to generate answer: {str(e)}")

    with tab2:
        st.header("❓ Ask Questions")
        if "selected_project" not in st.session_state or st.session_state.selected_project is None:
            st.warning("Please select a project from the sidebar.")
        else:
            project_id, project_name, project_path, _ = st.session_state.selected_project
            question = st.text_input("Your question:")
            if question:
                with st.spinner("Analyzing content..."):
                    try:
                        context, chunks = database_manager.get_RAG_question_context(question, project_id)
                        print(context)
                        response = client.generate_answer(context)
                        st.info(f"**Answer:** {response}")
                    except Exception as e:
                        st.error(f"Failed to generate answer: {str(e)}")

    with tab3:  # Mind Map
        st.header("🧠 Interactive Mind Map")
        if "selected_project" not in st.session_state or st.session_state.selected_project is None:
            st.warning("Please select a project from the sidebar.")
        else:
            project_id, project_name, project_path, _ = st.session_state.selected_project
            topic = st.text_input("On what topic do you want to build a mind map?")
            if topic:
                with st.spinner("Analyzing content..."):
                    try:
                        context, chunks = database_manager.get_RAG_mind_map_contex(topic, project_id)
                        print(context)
                        graph_save_path = os.path.join(project_path, "mindmaps", f"{topic}.json")
                        os.makedirs(os.path.dirname(graph_save_path), exist_ok=True)
                        graph.initialize_mindmap(context, graph_save_path)
                    except Exception as e:
                        st.error(f"Failed to generate answer: {str(e)}")

        # Display mind map if exists
        if 'mindmap' in st.session_state and st.session_state.mindmap['graph']:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Show Full View"):
                    st.session_state.mindmap['current_root'] = st.session_state.mindmap['initial_root']
                    st.rerun()
            
            # Draw the interactive mind map
            graph.draw_interactive_mindmap()
            
            # Node information
            if st.session_state.mindmap.get('selected_node'):
                node = st.session_state.mindmap['selected_node']
                desc = st.session_state.mindmap['graph'].nodes[node].get('desc', 'No description available')
                st.markdown(f"**{node}**")
                st.write(desc)
        else:
            st.info("You can now generate a mind map based on the selected PDF")

    with tab4:  # Quiz
        st.header("📝 Knowledge Check")

        if "selected_project" not in st.session_state or st.session_state.selected_project is None:
            st.warning("Please select a project from the sidebar.")
        else:
            project_id, project_name, project_path, _ = st.session_state.selected_project
            
            with st.expander("⚙️ Quiz Settings", expanded=True):
                cols = st.columns(3)
                with cols[0]:
                    num_questions = st.slider("Questions", 3, 15, 5)
                with cols[1]:
                    difficulty = st.selectbox("Level", ["Easy", "Medium", "Hard"])
                with cols[2]:
                    topic = st.text_input("Topic", "General Knowledge")
                
                if st.button("✨ Generate New Quiz"):
                    with st.spinner("Creating quiz..."):
                        try:
                            context, chunks = database_manager.get_RAG_context(topic, project_id, top_k=15)
                            quiz_json_path = os.path.join(project_path, "quizzes", f"{topic}.json")
                            os.makedirs(os.path.dirname(quiz_json_path), exist_ok=True)
                            quiz_raw = pdf_handler.generate_quiz_questions(
                                context,
                                num_questions=num_questions,
                                difficulty=difficulty
                            )
                            
                            if not quiz_raw:
                                st.error("Failed to generate quiz content")
                                st.stop()
                                
                            questions = pdf_handler.parse_quiz_questions(quiz_raw,
                                quiz_json_path=quiz_json_path)
                            
                            if not questions:
                                st.error("No valid questions parsed")
                                st.stop()
                                
                            st.session_state.quiz_data = {
                                'questions': questions,
                                'index': 0,
                                'score': 0,
                                'active': True,
                                'answered': {}
                            }
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Quiz creation failed: {str(e)}")

            # Quiz display logic
            if st.session_state.get('quiz_data', {}).get('active'):
                quiz = st.session_state.quiz_data
                if not quiz['questions']:
                    st.warning("Quiz generated but no questions available")
                    st.stop()
                    
                current = quiz['questions'][quiz['index']]
                
                st.progress((quiz['index']+1)/len(quiz['questions']))
                st.subheader(f"Question {quiz['index']+1}")
                st.write(current['question'])
                
                selected = st.radio("Options:", current['options'], key=f"q_{quiz['index']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Submit Answer"):
                        if selected == current['answer']:
                            st.success("Correct!")
                            if quiz['index'] not in quiz['answered']:
                                quiz['score'] += 1
                        else:
                            st.error(f"Correct answer: {current['answer']}")
                        quiz['answered'][quiz['index']] = True
                with col2:
                    if quiz['index'] < len(quiz['questions'])-1:
                        if st.button("Next Question"):
                            quiz['index'] += 1
                            st.rerun()
                    else:
                        if st.button("Finish Quiz"):
                            st.balloons()
                            st.success(f"Final score: {quiz['score']}/{len(quiz['questions'])}")
                            quiz['active'] = False