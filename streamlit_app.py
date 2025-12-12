import streamlit as st
from openai import OpenAI

# Title and description
st.title("💬 Chatbot — 모델 테스트용 인터페이스")
st.write(
    "간단한 챗봇 테스트 앱입니다. 사이드바의 모델 설정을 사용해 모델, 시스템 프롬프트, "
    "Temperature, Max Tokens을 조절하며 테스트할 수 있습니다."
)

# Ask user for their OpenAI API key
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client
    client = OpenAI(api_key=openai_api_key)

    # -- Sidebar: collapsible model/settings panel
    with st.sidebar.expander("Model Settings (접었다 펼치기)", expanded=False):
        model = st.selectbox(
            "Model",
            options=["gpt-4o", "gpt-4", "gpt-3.5-turbo-16k", "gpt-3.5-turbo"],
            index=3,
            help="테스트할 모델을 선택하세요."
        )

        system_prompt = st.text_area(
            "System Prompt (시스템 프롬프트)",
            value="",
            help="어시스턴트의 동작을 지시하는 시스템 프롬프트를 입력하세요."
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.01,
            help="응답의 무작위성(창의성)을 조절합니다."
        )

        max_tokens = st.slider(
            "Max Tokens",
            min_value=64,
            max_value=4096,
            value=512,
            step=1,
            help="응답으로 생성할 최대 토큰 수를 설정합니다."
        )

        # Quiz mode controls in sidebar
        st.sidebar.markdown("---")
        quiz_mode = st.sidebar.checkbox("구구단 퀴즈 모드", value=False)
        if quiz_mode:
            if "quiz_active" not in st.session_state or not st.session_state.quiz_active:
                if st.sidebar.button("퀴즈 시작"):
                    st.session_state.quiz_active = True
                    st.session_state.quiz_turn = "assistant_asks"
                    st.session_state.quiz_score_user = 0
                    st.session_state.quiz_score_bot = 0
                    st.session_state.quiz_qcount = 0
                    st.session_state.quiz_expected = None
                    st.session_state.messages.append({"role": "assistant", "content": "구구단 퀴즈를 시작할게요! 먼저 제가 문제를 내겠습니다."})
            else:
                if st.sidebar.button("퀴즈 종료"):
                    st.session_state.quiz_active = False
                    st.session_state.messages.append({"role": "assistant", "content": f"퀴즈를 종료합니다. 최종 점수 — 당신: {st.session_state.quiz_score_user}, 챗봇: {st.session_state.quiz_score_bot}"})

    # Initialize messages in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display previous chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat / Quiz input handling
    if "quiz_active" in st.session_state and st.session_state.get("quiz_active"):
        # Quiz mode: alternate between assistant asking and user asking
        if st.session_state.quiz_turn == "assistant_asks":
            # If no expected question, generate one and present it
            if not st.session_state.get("quiz_expected"):
                import random
                a = random.randint(2, 9)
                b = random.randint(1, 9)
                question = f"{a} x {b} = ?"
                st.session_state.quiz_expected = a * b
                st.session_state.quiz_qcount += 1
                st.session_state.messages.append({"role": "assistant", "content": f"문제 {st.session_state.quiz_qcount}: {question}"})

            if answer := st.chat_input("문제의 정답을 입력하세요 (숫자만):"):
                st.session_state.messages.append({"role": "user", "content": answer})
                with st.chat_message("user"):
                    st.markdown(answer)

                # Try to parse numeric answer
                try:
                    user_val = int(''.join(ch for ch in answer if ch.isdigit()))
                except Exception:
                    user_val = None

                if user_val is not None and st.session_state.quiz_expected is not None and user_val == st.session_state.quiz_expected:
                    feedback = "정답이에요! 잘했어요 🎉"
                    st.session_state.quiz_score_user += 1
                else:
                    feedback = f"틀렸어요. 정답은 {st.session_state.quiz_expected} 입니다."

                st.session_state.messages.append({"role": "assistant", "content": feedback})
                st.session_state.quiz_expected = None
                st.session_state.quiz_turn = "user_asks"

        elif st.session_state.quiz_turn == "user_asks":
            # Prompt the user to 입력 a multiplication question for the bot
            if user_q := st.chat_input("이제 당신이 챗봇에게 문제를 내보세요 (예: 3x4 또는 7 x 8):"):
                st.session_state.messages.append({"role": "user", "content": user_q})
                with st.chat_message("user"):
                    st.markdown(user_q)

                # Parse user's question
                import re
                m = re.search(r"(\d+)\s*[x×\*]\s*(\d+)", user_q.replace('X','x'))
                if m:
                    a = int(m.group(1))
                    b = int(m.group(2))
                    bot_answer = a * b
                    st.session_state.messages.append({"role": "assistant", "content": f"제가 답할게요: {a} x {b} = {bot_answer}"})
                    st.session_state.quiz_score_bot += 1
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "문제를 잘 이해하지 못했어요. '3x4' 형태로 입력해 주세요."})

                st.session_state.quiz_turn = "assistant_asks"

    else:
        # Normal chat mode using API
        if prompt := st.chat_input("메시지를 입력하세요..."):

            # Store and display the user's prompt
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Build messages list for API: include system prompt first if provided
            api_messages = []
            if system_prompt and system_prompt.strip():
                api_messages.append({"role": "system", "content": system_prompt})

            api_messages.extend([
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ])

            # Call OpenAI chat completion with chosen settings
            stream = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=float(temperature),
                max_tokens=int(max_tokens),
                stream=True,
            )

            # Stream response to the chat and store it
            with st.chat_message("assistant"):
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})
