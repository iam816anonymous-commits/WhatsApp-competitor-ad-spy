import streamlit as st
from app.db.database import get_session
from app.models.models import User, Organization

def render_auth_ui():
    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.user:
        st.subheader("Login to Winner Intelligence OS")
        email = st.text_input("Email")
        if st.button("Login"):
            # Mock Auth
            session = get_session()
            user = session.query(User).filter_by(email=email).first()
            if not user:
                # Auto-create for demo
                org = Organization(name=f"{email}'s Org")
                session.add(org)
                session.flush()
                user = User(email=email, org_id=org.id)
                session.add(user)
                session.commit()

            st.session_state.user = {"email": user.email, "org_id": user.org_id, "role": user.role}
            st.rerun()
    else:
        st.sidebar.write(f"Logged in as: {st.session_state.user['email']}")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
