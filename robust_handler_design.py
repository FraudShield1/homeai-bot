async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Unified Natural Language Handler
    Logic Flow:
    1. Greeting Check -> Fast Chat
    2. Command Analysis (LLM) -> Execute Command
    3. General Chat (LLM) -> Conversational Response
    4. Fallback -> Help Message
    """
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # 0. Send typing indicator immediately
    await update.message.reply_chat_action("typing")

    try:
        # A. Gather Context (History + Home State)
        history = []
        if conversation_memory:
            history = conversation_memory.get_history(user_id)
        
        # B. FAST PATH: Greetings
        # Don't waste time analyzing "Hi" for home automation commands
        if message_text.lower() in ["hi", "hello", "hey", "start", "yo", "gm", "gn"]:
            if llm.enabled:
                response = await llm.chat(message_text, context={"history": history})
                
                # Save to memory
                if conversation_memory:
                    conversation_memory.add_message(user_id, "user", message_text)
                    conversation_memory.add_message(user_id, "assistant", response)
                    
                await update.message.reply_text(response)
                return

        # C. SMARTER PATH: LLM Analysis
        if llm.enabled:
            # 1. Get Home State (for context awareness)
            home_context = {}
            try:
                states = await ha.get_all_states()
                home_context = {
                    "lights_on": sum(1 for s in states if s.get("entity_id", "").startswith("light.") and s.get("state") == "on"),
                    "temperature": next((s.get("state") for s in states if "temperature" in s.get("entity_id", "")), "unknown")
                }
            except: 
                home_context = {}

            # 2. Analyze Intent
            # asking: "Is this a command or just chat?"
            analysis = await llm.analyze_command(message_text, context=home_context)
            
            # 3. Decision Tree
            if analysis and analysis.get("action") and analysis.get("confidence", 0) > 0.6:
                # >>> IT IS A COMMAND
                success = await execute_smart_command(analysis, update)
                
                if success and conversation_memory:
                    conversation_memory.add_message(user_id, "user", message_text)
                    conversation_memory.add_message(user_id, "system", f"Action taken: {analysis['action']}")
                return
            
            else:
                # >>> IT IS A CHAT (or ambiguous)
                # Fallback to chat personality
                response = await llm.chat(message_text, context={"history": history, "home_state": home_context})
                
                if response:
                    if conversation_memory:
                        conversation_memory.add_message(user_id, "user", message_text)
                        conversation_memory.add_message(user_id, "assistant", response)
                    await update.message.reply_text(response)
                    return
        
        # D. FALLBACK (LLM Disabled or Failed completely)
        # Try basic regex parser
        command_info = parse_natural_command(message_text.lower())
        if command_info:
            # Execute basic command...
            # (Reuse execution logic)
            pass
        else:
            await update.message.reply_text("I'm listening, but I'm not sure if you want me to do something or just chat. Try 'Turn on lights' or ask me a question!")

    except Exception as e:
        logger.error(f"NL Handler Error: {e}")
        await update.message.reply_text(f"✨ I tripped over a wire. Error: {str(e)}")
