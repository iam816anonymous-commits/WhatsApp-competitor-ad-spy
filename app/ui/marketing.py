import streamlit as st

def render_landing_page():
    st.title("🚀 Winner Intelligence OS")
    st.subheader("The #1 Platform for Profit-First Marketers")

    st.write("""
    Stop guessing what ads to run. Our AI-powered OS identifies 'Winners' in real-time by
    tracking longevity, creative reuse, and offer shifts across 4 platforms.
    """)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🎯 **Winner Scoring**\nScale of 0-100 based on market data.")
    with col2:
        st.success("🌳 **Clone Detection**\nSee the family tree of every creative.")
    with col3:
        st.warning("🔔 **Real-time Alerts**\nKnow the moment a competitor drops a price.")

    st.divider()
    st.header("Pricing")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.subheader("Starter")
        st.write("$99/mo")
        st.write("- 5 Winner Reports")
        st.write("- 1 Platform")
        if st.button("Get Started", key="p1"):
            st.session_state.show_onboarding = True
            st.rerun()

    with p2:
        st.subheader("Professional")
        st.write("$299/mo")
        st.write("- 50 Winner Reports")
        st.write("- All Platforms")
        if st.button("Scale Now", key="p2"):
            st.session_state.show_onboarding = True
            st.rerun()

    with p3:
        st.subheader("Agency")
        st.write("$999/mo")
        st.write("- Unlimited Reports")
        st.write("- Custom Watchlists")
        if st.button("Go Enterprise", key="p3"):
            st.session_state.show_onboarding = True
            st.rerun()

def render_onboarding():
    st.title("Welcome to the Winner's Circle")
    step = st.session_state.get("onboarding_step", 1)

    if step == 1:
        st.subheader("Step 1: Your Focus")
        niche = st.selectbox("Primary Niche", ["Skincare", "Fashion", "SaaS", "Ecom"])
        if st.button("Next"):
            st.session_state.onboarding_step = 2
            st.rerun()
    elif step == 2:
        st.subheader("Step 2: Competitors")
        brands = st.text_input("Enter 3 Competitor Brands (comma separated)")
        if st.button("Finish Setup"):
            st.session_state.user_ready = True
            st.session_state.show_onboarding = False
            st.rerun()
