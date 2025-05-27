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
    st.title(f"📚 Study Assistant - {st.session_state.username}")

    # sidebar
    with st.sidebar:
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

    # main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 Materials", "❓ Ask Question", "🗺️ Mind Map", "📝 Quiz", "🃏 Flashcards"])

    with tab1:
        st.header("PDF Tools")

        if "selected_project" not in st.session_state or st.session_state.selected_project is None:
            st.warning("Please select a project from the sidebar.")
        else:
            project_id, project_name, project_path, _ = st.session_state.selected_project
            st.session_state.uploaded_pdfs = database_manager.get_all_documents(project_id)

            uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
            if uploaded_file:
                os.makedirs(os.path.join(project_path, "documents"), exist_ok=True)
                save_path = os.path.join(project_path, "documents", uploaded_file.name)

                doc_id = database_manager.insert_document(project_id, uploaded_file.name, uploaded_file.name)

                if doc_id is not None:
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.session_state.uploaded_pdfs[uploaded_file.name] = doc_id
                    database_manager.parse_insert_document(project_id, doc_id)
            else:
                st.warning("No file uploaded yet.")

            if st.session_state.uploaded_pdfs:
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
                            if os.path.exists(pdf_path):
                                os.remove(pdf_path)

                            doc_id = st.session_state.uploaded_pdfs[st.session_state.selected_pdf]
                            database_manager.delete_document(doc_id)

                            st.success(f"Deleted {st.session_state.selected_pdf} from database and disk.")
                            del st.session_state.uploaded_pdfs[st.session_state.selected_pdf]
                            st.session_state.selected_pdf = None
                            st.rerun()

                        except Exception as e:
                            st.error(f"Failed to delete PDF: {str(e)}")

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

    with tab3: 
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

        if 'mindmap' in st.session_state and st.session_state.mindmap['graph']:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Show Full View"):
                    st.session_state.mindmap['current_root'] = st.session_state.mindmap['initial_root']
                    st.rerun()
            
            graph.draw_interactive_mindmap()

            if st.session_state.mindmap.get('selected_node'):
                node = st.session_state.mindmap['selected_node']
                desc = st.session_state.mindmap['graph'].nodes[node].get('desc', 'No description available')
                st.markdown(f"**{node}**")
                st.write(desc)
        else:
            st.info("You can now generate a mind map based on the selected PDF")

    with tab4: 
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

    with tab5:
        st.header("🃏 Flashcards")

        project_selected = "selected_project" in st.session_state and st.session_state.selected_project is not None

        if not project_selected:
            st.warning("Please select a project from the sidebar.")
        else:
            project_id, project_name, project_path, _ = st.session_state.selected_project
            flashcard_json_path = os.path.join(project_path, "flashcards", "approved.json")
            os.makedirs(os.path.dirname(flashcard_json_path), exist_ok=True)

            if "approved_flashcards" not in st.session_state:
                st.session_state.approved_flashcards = pdf_handler.load_flashcard_list(flashcard_json_path)

            if "learning_mode" not in st.session_state:
                st.session_state.learning_mode = False
            if "learning_index" not in st.session_state:
                st.session_state.learning_index = 0
            if "card_flipped" not in st.session_state:
                st.session_state.card_flipped = False

            if not st.session_state.learning_mode:
                if st.button("🎯 Start Learning"):
                    if st.session_state.approved_flashcards:
                        st.session_state.learning_mode = True
                        st.session_state.learning_index = 0
                        st.session_state.card_flipped = False
                        st.rerun()  
                    else:
                        st.warning("No flashcards to learn!")
            else:
                if st.button("🏁 Finish Learning"):
                    st.session_state.learning_mode = False
                    st.session_state.card_flipped = False
                    st.rerun() 

            if st.session_state.approved_flashcards:
                if st.session_state.learning_mode:
                    idx = st.session_state.learning_index
                    card = st.session_state.approved_flashcards[idx]

                    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
                    with header_col1:
                        st.subheader(f"Flashcard {idx + 1} of {len(st.session_state.approved_flashcards)}")
                    with header_col2:
                        if st.button("✏️ Edit", key="edit_card"):
                            st.session_state.original_flashcard = card.copy() 
                            st.session_state.current_flashcard = card.copy()  
                            st.session_state.generating_flashcard = True
                            st.session_state.learning_mode = False 
                            st.rerun()
                    with header_col3:
                        if st.button("❌ Delete", key="delete_card"):
                            st.session_state.approved_flashcards.pop(idx)
                            pdf_handler.save_flashcard_list(st.session_state.approved_flashcards, flashcard_json_path)
                            if st.session_state.learning_index >= len(st.session_state.approved_flashcards):
                                st.session_state.learning_index = max(0, len(st.session_state.approved_flashcards) - 1)
                            if not st.session_state.approved_flashcards:
                                st.session_state.learning_mode = False
                            st.session_state.card_flipped = False
                            st.rerun()

                    st.markdown("---")

                    col_left, col_center, col_right = st.columns([1, 3, 1])
                    with col_center:
                        if st.session_state.card_flipped:
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #d4edda; 
                                    border: 2px solid #c3e6cb; 
                                    border-radius: 10px; 
                                    padding: 30px; 
                                    text-align: center; 
                                    min-height: 200px; 
                                    display: flex; 
                                    align-items: center; 
                                    justify-content: center;
                                    font-size: 18px;
                                ">
                                    <div>{card['back']}</div>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #d1ecf1; 
                                    border: 2px solid #bee5eb; 
                                    border-radius: 10px; 
                                    padding: 30px; 
                                    text-align: center; 
                                    min-height: 200px; 
                                    display: flex; 
                                    align-items: center; 
                                    justify-content: center;
                                    font-size: 18px;
                                ">
                                    <div>{card['front']}</div>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )

                    st.markdown("<br>", unsafe_allow_html=True)

                    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 1, 1])

                    with nav_col1:
                        if st.button("⬅️ Previous", disabled=(idx == 0)):
                            st.session_state.learning_index -= 1
                            st.session_state.card_flipped = False
                            st.rerun()

                    with nav_col2:
                        st.write("") 

                    with nav_col3:
                        if st.button("🔄 Flip", key="flip_card"):
                            st.session_state.card_flipped = not st.session_state.card_flipped
                            st.rerun()

                    with nav_col4:
                        st.write("") 

                    with nav_col5:
                        if st.button("➡️ Next", disabled=(idx == len(st.session_state.approved_flashcards) - 1)):
                            st.session_state.learning_index += 1
                            st.session_state.card_flipped = False
                            st.rerun()

                else:
                    st.subheader("✅ Your Flashcards")
                    flashcards = st.session_state.approved_flashcards
                    cols = st.columns(3)

                    for idx, card in enumerate(flashcards):
                        col = cols[idx % 3]
                        with col:
                            st.markdown(f"**{idx + 1}.** {card['front']}")

            else:
                st.info("No approved flashcards yet.")

            st.markdown("---")

            col_generate, col_empty = st.columns([1, 3])
            with col_generate:
                if st.button("➕ Generate New Flashcard"):
                    st.session_state.generating_flashcard = True
                    st.rerun()

            if st.session_state.get('generating_flashcard'):
                st.markdown("### ✨ Flashcard Generator")

                is_editing = st.session_state.get('original_flashcard') is not None
                if not st.session_state.get('current_flashcard') and not is_editing:
                    with st.spinner("Generating a new flashcard..."):
                        try:
                            context, _ = database_manager.get_RAG_context("General", project_id, top_k=15)
                            flashcard_raw = pdf_handler.generate_flashcards(context, num_cards=1)
                            flashcards = pdf_handler.parse_flashcards(flashcard_raw)
                            if flashcards:
                                st.session_state.current_flashcard = flashcards[0]
                                st.success("New flashcard generated!")
                                st.rerun()  
                            else:
                                st.error("Failed to generate a valid flashcard")
                        except Exception as e:
                            st.error(f"Flashcard generation error: {str(e)}")
                            st.session_state.generating_flashcard = False

                if st.session_state.get('current_flashcard'):
                    card = st.session_state['current_flashcard']
                    if is_editing:
                        st.info("🔧 Editing existing flashcard")
                    else:
                        st.info("✨ Creating new flashcard")
                    
                    front = st.text_input("Front (Question)", card['front'], key="gen_front")
                    back = st.text_area("Back (Answer)", card['back'], key="gen_back")

                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("✅ Approve", key="approve_btn"):
                            updated_card = {'front': front, 'back': back}
                            found_idx = None
                            original_card = st.session_state.get('original_flashcard')
                            if original_card:
                                for i, c in enumerate(st.session_state.approved_flashcards):
                                    if c['front'] == original_card['front'] and c['back'] == original_card['back']:
                                        found_idx = i
                                        break
                            
                            if found_idx is not None:
                                st.session_state.approved_flashcards[found_idx] = updated_card
                                st.success("Flashcard updated!")
                            else:
                                st.session_state.approved_flashcards.append(updated_card)
                                st.success("New flashcard added!")

                            pdf_handler.save_flashcard_list(st.session_state.approved_flashcards, flashcard_json_path)
                            st.session_state.current_flashcard = None
                            st.session_state.generating_flashcard = False
                            st.session_state.original_flashcard = None
                            st.rerun()

                    with col2:
                        if st.button("✏️ Modify", key="modify_btn"):
                            st.session_state.current_flashcard = {'front': front, 'back': back}
                            st.info("Flashcard updated!")

                    with col3:
                        if st.button("🔄 Regenerate", key="regenerate_btn"):
                            st.session_state.current_flashcard = None
                            st.rerun()

                    with col4:
                        if st.button("🚪 Finish", key="finish_btn"):
                            st.session_state.current_flashcard = None
                            st.session_state.generating_flashcard = False
                            st.rerun()