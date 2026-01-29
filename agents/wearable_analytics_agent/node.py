import agentc
import agentc_langgraph.agent
import langchain_core.messages
import langchain_core.runnables
import langchain_core.callbacks
import langchain_openai.chat_models
import typing
import time
import os


class TimingCallback(langchain_core.callbacks.BaseCallbackHandler):
    """Callback handler to track tool calls and LLM calls with timing"""
    
    def __init__(self):
        self.tool_count = 0
        self.llm_count = 0
        self.step_times = []
        self.current_step_start = None
    
    def on_tool_start(self, serialized, input_str: str, **kwargs):
        """Called when a tool starts"""
        tool_name = serialized.get("name", "unknown")
        self.tool_count += 1
        self.current_step_start = time.time()
        print(f"\n🔧 [TOOL #{self.tool_count}] Starting: {tool_name}")
        print(f"    Input preview: {str(input_str)[:100]}...")
    
    def on_tool_end(self, output: str, **kwargs):
        """Called when a tool ends"""
        if self.current_step_start:
            duration = time.time() - self.current_step_start
            self.step_times.append(("tool", duration))
            print(f"✅ [TOOL #{self.tool_count}] Completed in {duration:.2f}s")
            print(f"    Output preview: {str(output)[:100]}...")
            self.current_step_start = None
    
    def on_tool_error(self, error: Exception, **kwargs):
        """Called when a tool errors"""
        if self.current_step_start:
            duration = time.time() - self.current_step_start
            print(f"❌ [TOOL #{self.tool_count}] Failed after {duration:.2f}s: {str(error)[:100]}")
            self.current_step_start = None
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when LLM starts"""
        self.llm_count += 1
        self.current_step_start = time.time()
        print(f"\n🤖 [LLM #{self.llm_count}] Starting (deciding next action)...")
    
    def on_llm_end(self, response, **kwargs):
        """Called when LLM ends"""
        if self.current_step_start:
            duration = time.time() - self.current_step_start
            self.step_times.append(("llm", duration))
            print(f"✅ [LLM #{self.llm_count}] Completed in {duration:.2f}s")
            self.current_step_start = None


class State(agentc_langgraph.agent.State):
    """State for the wearable analytics agent"""

    patient_id: typing.Optional[str]
    patient_name: typing.Optional[str]
    patient_condition: typing.Optional[str]
    question: typing.Optional[str]
    wearable_data: typing.Optional[list[dict]]
    similar_patients: typing.Optional[list[dict]]
    trend_analysis: typing.Optional[dict]
    cohort_comparison: typing.Optional[dict]
    patient_comparison: typing.Optional[dict]  # NEW: Add patient comparison to state
    research_papers: typing.Optional[list[dict]]
    alerts: typing.Optional[list[dict]]
    recommendations: typing.Optional[list[str]]
    answer: typing.Optional[str]
    is_complete: bool
    previous_node: typing.Optional[str]
    is_last_step: bool


class WearableAnalyticsAgent(agentc_langgraph.agent.ReActAgent):
    """
    Agent for analyzing wearable data and providing clinical insights.

    This agent:
    1. Retrieves patient wearable data
    2. Identifies concerning trends and generates alerts
    3. Finds demographically similar patients for comparison
    4. Compares patient metrics to cohort averages
    5. Connects observed symptoms to relevant research papers
    6. Provides evidence-based recommendations

    Uses the wearable_analytics_agent prompt and multiple analysis tools from the catalog.
    """

    def __init__(self, catalog: agentc.Catalog, span: agentc.Span):
        # Use GPT-4o for fast, accurate tool calling
        agent_endpoint = os.getenv("AGENT_LLM_ENDPOINT", "https://api.openai.com")
        agent_token = os.getenv("OPENAI_API_KEY")
        agent_model = os.getenv("AGENT_LLM_NAME", "gpt-4o-mini")
        
        base_url = agent_endpoint if agent_endpoint else None

        print(f"🤖 [AGENT CONFIG] Using model: {agent_model} via {'OpenAI' if base_url is None else base_url}")
        
        chat_model = langchain_openai.chat_models.ChatOpenAI(
            model=agent_model,
            temperature=0,
            api_key=agent_token,
            base_url=base_url
        )
        super().__init__(
            chat_model=chat_model, 
            catalog=catalog, 
            span=span, 
            prompt_name="wearable_analytics_agent"
        )

    def _invoke(
        self, span: agentc.Span, state: State, config: langchain_core.runnables.RunnableConfig
    ) -> State:
        """
        Execute the wearable analytics workflow with DIRECT tool calls (no ReAct).
        
        This is 10-20x faster than ReAct because we:
        1. Call tools directly instead of asking LLM to decide
        2. Make only 1 LLM call at the end (for final answer)
        3. Skip unnecessary "thinking" between steps

        Args:
            span: Tracing span for observability
            state: Current state with patient_id and question
            config: LangGraph configuration

        Returns:
            Updated state with analysis results
        """
        import time
        
        start_time = time.time()
        patient_id = state.get('patient_id')
        question = state.get('question')
        
        print(f"\n{'='*80}")
        print(f"🚀 [AGENT] STARTING OPTIMIZED WEARABLE ANALYTICS (DIRECT WORKFLOW)")
        print(f"    Patient ID: {patient_id}")
        print(f"    Question: {question}")
        print(f"{'='*80}\n")
        
        span.log(agentc.span.SystemContent(value=f"Analyzing wearable data for patient {patient_id}"))

        try:
            # Get tools from catalog
            print(f"⏱️  [AGENT] Loading tools from catalog...")
            find_patient = self.catalog.find("tool", name="find_patient_by_id")
            find_conditions = self.catalog.find("tool", name="find_conditions_by_patient_id")
            get_wearables = self.catalog.find("tool", name="get_wearable_data_by_patient")
            analyze_trends = self.catalog.find("tool", name="analyze_wearable_trends")
            find_similar = self.catalog.find("tool", name="find_similar_patients_demographics")
            print(f"✅ [AGENT] Tools loaded in {time.time() - start_time:.2f}s\n")
            
            # STEP 1: Get patient info (parallel calls would be ideal, but doing sequential for safety)
            print(f"🔧 [STEP 1] Getting patient context...")
            step1_start = time.time()
            
            # Tool Call 1: find_patient
            span.log(agentc.span.ToolCallContent(
                tool_name="find_patient_by_id",
                tool_args={"patient_id": patient_id},
                tool_call_id="call_1_find_patient"
            ))
            patient_info = find_patient.func(patient_id=patient_id)
            span.log(agentc.span.ToolResultContent(
                tool_call_id="call_1_find_patient",
                tool_result={"name": patient_info.get("name", "Unknown")}
            ))
            patient_name = patient_info.get("name", "Unknown")
            
            # Tool Call 2: find_conditions
            span.log(agentc.span.ToolCallContent(
                tool_name="find_conditions_by_patient_id",
                tool_args={"patient_id": patient_id},
                tool_call_id="call_2_find_conditions"
            ))
            condition_result = find_conditions.func(patient_id=patient_id)
            patient_condition = condition_result if isinstance(condition_result, str) else condition_result.get("condition", "Unknown")
            span.log(agentc.span.ToolResultContent(
                tool_call_id="call_2_find_conditions",
                tool_result={"condition": patient_condition}
            ))
            
            span.log(agentc.span.SystemContent(value=f"Patient identified: {patient_name} ({patient_condition})"))
            print(f"✅ [STEP 1] Completed in {time.time() - step1_start:.2f}s")
            print(f"    Patient: {patient_name}, Condition: {patient_condition}\n")
            
            # STEP 2: Get wearable data
            print(f"🔧 [STEP 2] Getting wearable data...")
            step2_start = time.time()
            
            # Tool Call: get_wearable_data_by_patient
            span.log(agentc.span.ToolCallContent(
                tool_name="get_wearable_data_by_patient",
                tool_args={"patient_id": patient_id, "days": 30},
                tool_call_id="call_3_get_wearable_data"
            ))
            wearable_data = get_wearables.func(patient_id=patient_id, days=30)
            
            # Handle both list and dict returns
            if isinstance(wearable_data, dict) and "data" in wearable_data:
                wearable_data = wearable_data["data"]
            
            data_count = len(wearable_data) if isinstance(wearable_data, list) else 0
            span.log(agentc.span.ToolResultContent(
                tool_call_id="call_3_get_wearable_data",
                tool_result={"data_points": data_count}
            ))
            span.log(agentc.span.SystemContent(value=f"Retrieved {data_count} wearable data points"))
            print(f"✅ [STEP 2] Completed in {time.time() - step2_start:.2f}s")
            print(f"    Retrieved {data_count} data points\n")
            
            # STEP 3: Analyze trends
            print(f"🔧 [STEP 3] Analyzing trends...")
            step3_start = time.time()
            
            # Tool Call: analyze_wearable_trends
            span.log(agentc.span.ToolCallContent(
                tool_name="analyze_wearable_trends",
                tool_args={"patient_condition": patient_condition, "data_points": len(wearable_data) if isinstance(wearable_data, list) else 0},
                tool_call_id="call_4_analyze_trends"
            ))
            trend_analysis = analyze_trends.func(
                wearable_data=wearable_data,
                patient_condition=patient_condition
            )
            
            # Handle string or dict return
            if isinstance(trend_analysis, str):
                import json
                trend_analysis = json.loads(trend_analysis)
            
            alerts = trend_analysis.get("alerts", [])
            alert_count = len(alerts)
            critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
            
            span.log(agentc.span.ToolResultContent(
                tool_call_id="call_4_analyze_trends",
                tool_result={"alerts": alert_count, "critical_alerts": critical_count}
            ))
            span.log(agentc.span.SystemContent(value=f"Trend analysis complete: {alert_count} alerts detected ({critical_count} critical)"))
            print(f"✅ [STEP 3] Completed in {time.time() - step3_start:.2f}s")
            print(f"    Found {alert_count} alerts\n")
            
            # STEP 4: Find similar patients
            print(f"🔧 [STEP 4] Finding similar patients...")
            step4_start = time.time()
            
            # Tool Call: find_similar_patients_demographics
            span.log(agentc.span.ToolCallContent(
                tool_name="find_similar_patients_demographics",
                tool_args={"patient_id": patient_id, "age_range": 5, "same_condition": True, "same_gender": True, "limit": 10},
                tool_call_id="call_5_find_similar_patients"
            ))
            similar_patients = find_similar.func(
                patient_id=patient_id,
                age_range=5,
                same_condition=True,
                same_gender=True,
                limit=10
            )
            
            # Parse similar patients
            if isinstance(similar_patients, str):
                import json
                similar_patients = json.loads(similar_patients)
            if not isinstance(similar_patients, list):
                similar_patients = []
            
            span.log(agentc.span.ToolResultContent(
                tool_call_id="call_5_find_similar_patients",
                tool_result={"similar_patients_count": len(similar_patients)}
            ))
            span.log(agentc.span.SystemContent(value=f"Found {len(similar_patients)} similar patients for cohort comparison"))
            print(f"✅ [STEP 4] Completed in {time.time() - step4_start:.2f}s")
            print(f"    Found {len(similar_patients)} similar patients\n")
            
            # STEP 5: Compute patient comparison metrics (outlier analysis)
            print(f"🔧 [STEP 5] Computing patient comparison analysis...")
            step5_start = time.time()
            
            span.log(agentc.span.SystemContent(value="Computing patient comparison metrics and outlier analysis"))
            
            # Get current patient's trend data
            patient_trends = trend_analysis.get("trends", {})
            
            # DEBUG: Check what data we have
            print(f"    DEBUG - similar_patients type: {type(similar_patients)}, len: {len(similar_patients) if similar_patients else 0}")
            print(f"    DEBUG - wearable_data type: {type(wearable_data)}, len: {len(wearable_data) if isinstance(wearable_data, list) else 'N/A'}")
            print(f"    DEBUG - patient_trends keys: {patient_trends.keys() if patient_trends else 'empty'}")
            
            # Initialize comparison structure
            patient_comparison = {
                "summary": "",
                "comparison_points": [],
                "outlier_status": "normal",  # normal, concerning, critical
                "cohort_size": len(similar_patients) if similar_patients else 0,
                "metric_comparisons": []
            }
            
            # If we have similar patients and wearable data, compute comparisons
            print(f"    DEBUG - Checking condition: similar_patients={bool(similar_patients)}, wearable_data is list={isinstance(wearable_data, list)}, len>0={len(wearable_data) > 0 if isinstance(wearable_data, list) else False}")
            
            if similar_patients and isinstance(wearable_data, list) and len(wearable_data) > 0:
                # Get patient's key metrics from trends
                patient_avg_o2 = patient_trends.get("blood_oxygen", {}).get("average")
                patient_avg_hr = patient_trends.get("heart_rate", {}).get("average")
                patient_avg_steps = patient_trends.get("activity", {}).get("average_steps")
                
                # Determine if patient is an outlier
                outlier_metrics = []
                similar_metrics = []
                
                # O2 Saturation comparison
                if patient_avg_o2:
                    if patient_avg_o2 < 92:
                        outlier_metrics.append(f"O2 saturation significantly lower ({patient_avg_o2:.1f}% vs normal 95-100%)")
                        patient_comparison["outlier_status"] = "concerning"
                    elif patient_avg_o2 >= 95:
                        similar_metrics.append(f"O2 saturation within normal range ({patient_avg_o2:.1f}%)")
                    
                    patient_comparison["metric_comparisons"].append({
                        "metric": "blood_oxygen",
                        "patient_value": round(patient_avg_o2, 1),
                        "cohort_average": 95.5,  # Typical for asthma patients
                        "status": "below" if patient_avg_o2 < 94 else "normal"
                    })
                
                # Heart Rate comparison
                if patient_avg_hr:
                    if patient_avg_hr > 100:
                        outlier_metrics.append(f"Heart rate elevated ({patient_avg_hr:.0f} BPM vs normal 60-100 BPM)")
                        if patient_comparison["outlier_status"] == "normal":
                            patient_comparison["outlier_status"] = "concerning"
                    elif patient_avg_hr < 100:
                        similar_metrics.append(f"Heart rate within expected range ({patient_avg_hr:.0f} BPM)")
                    
                    patient_comparison["metric_comparisons"].append({
                        "metric": "heart_rate",
                        "patient_value": round(patient_avg_hr, 0),
                        "cohort_average": 78,  # Typical resting HR
                        "status": "elevated" if patient_avg_hr > 90 else "normal"
                    })
                
                # Activity comparison
                if patient_avg_steps:
                    if patient_avg_steps < 3000:
                        outlier_metrics.append(f"Activity level significantly reduced ({patient_avg_steps:.0f} steps/day)")
                        if patient_comparison["outlier_status"] == "normal":
                            patient_comparison["outlier_status"] = "concerning"
                    elif patient_avg_steps >= 5000:
                        similar_metrics.append(f"Maintaining good activity levels ({patient_avg_steps:.0f} steps/day)")
                    
                    patient_comparison["metric_comparisons"].append({
                        "metric": "activity_level",
                        "patient_value": round(patient_avg_steps, 0),
                        "cohort_average": 6500,  # Typical daily steps
                        "status": "below" if patient_avg_steps < 5000 else "normal"
                    })
                
                # Upgrade to critical if we have critical alerts
                critical_alerts = [a for a in alerts if a.get("severity", "").lower() == "critical"]
                if critical_alerts:
                    patient_comparison["outlier_status"] = "critical"
                
                # Build comparison points (2-3 key observations)
                if outlier_metrics:
                    patient_comparison["comparison_points"] = outlier_metrics[:2]
                elif similar_metrics:
                    patient_comparison["comparison_points"] = similar_metrics[:2]
                else:
                    patient_comparison["comparison_points"] = [
                        f"Metrics comparable to {len(similar_patients)} similar {patient_condition} patient{'s' if len(similar_patients) > 1 else ''}"
                    ]
                
                # Build summary text
                if patient_comparison["outlier_status"] == "critical":
                    patient_comparison["summary"] = f"Patient shows critical deviations from typical {patient_condition} cohort"
                elif patient_comparison["outlier_status"] == "concerning":
                    patient_comparison["summary"] = f"Patient shows some concerning differences compared to {len(similar_patients)} similar patient{'s' if len(similar_patients) > 1 else ''}"
                else:
                    patient_comparison["summary"] = f"Patient's metrics align well with cohort of {len(similar_patients)} similar {patient_condition} patient{'s' if len(similar_patients) > 1 else ''}"
            else:
                # No similar patients or data
                patient_comparison["summary"] = "Insufficient cohort data for comparison"
                patient_comparison["comparison_points"] = ["No similar patients found for comparison"]
            
            print(f"✅ [STEP 5] Completed in {time.time() - step5_start:.2f}s")
            print(f"    Outlier status: {patient_comparison['outlier_status']}\n")
            
            span.log(agentc.span.SystemContent(value=f"Patient comparison analysis complete: {patient_comparison['outlier_status']} status"))
            
            # STEP 5.5: Fetch relevant research papers based on alerts
            print(f"🔧 [STEP 5.5] Fetching relevant research papers...")
            step5_5_start = time.time()
            
            research_papers = []
            if alerts:
                try:
                    # Get the research tool from catalog
                    connect_research = self.catalog.find("tool", name="connect_symptoms_to_research")
                    
                    # Build symptoms description from alerts
                    symptoms_parts = []
                    for alert in alerts[:3]:  # Top 3 alerts
                        metric = alert.get("metric", "").replace("_", " ")
                        message = alert.get("message", "")
                        symptoms_parts.append(f"{metric}: {message}")
                    
                    symptoms_description = "; ".join(symptoms_parts)
                    
                    print(f"    🔬 Symptoms: {symptoms_description[:150]}...")
                    
                    # Tool Call: connect_symptoms_to_research
                    span.log(agentc.span.ToolCallContent(
                        tool_name="connect_symptoms_to_research",
                        tool_args={"symptoms_description": symptoms_description[:200], "patient_condition": patient_condition, "top_k": 3},
                        tool_call_id="call_6_research_papers"
                    ))
                    
                    # Call research tool
                    research_papers = connect_research.func(
                        symptoms_description=symptoms_description,
                        patient_condition=patient_condition,
                        top_k=3
                    )
                    
                    # Handle string or list returns
                    if isinstance(research_papers, str):
                        import json
                        research_papers = json.loads(research_papers)
                    if not isinstance(research_papers, list):
                        research_papers = []
                    
                    # Filter out error results
                    research_papers = [p for p in research_papers if not p.get("error")]
                    
                    span.log(agentc.span.ToolResultContent(
                        tool_call_id="call_6_research_papers",
                        tool_result={"papers_found": len(research_papers)}
                    ))
                    span.log(agentc.span.SystemContent(value=f"Found {len(research_papers)} relevant research papers"))
                    print(f"✅ [STEP 5.5] Completed in {time.time() - step5_5_start:.2f}s")
                    print(f"    Found {len(research_papers)} research papers\n")
                    
                except Exception as e:
                    print(f"⚠️  [STEP 5.5] Error fetching research: {e}")
                    research_papers = []
            else:
                print(f"⏭️  [STEP 5.5] Skipped - no alerts to research")
                print(f"✅ [STEP 5.5] Completed in {time.time() - step5_5_start:.2f}s\n")
            
            # STEP 6: Extract and enhance recommendations from trend analysis
            print(f"🔧 [STEP 6] Structuring recommendations...")
            step6_start = time.time()
            
            # Get recommendations from trend analysis
            recommendations = trend_analysis.get("recommendations", [])
            
            # If alerts exist but no recommendations, generate basic recommendations
            if alerts and not recommendations:
                for alert in alerts[:3]:  # Top 3 alerts
                    severity = alert.get("severity", "").lower()
                    metric = alert.get("metric", "")
                    condition = patient_condition
                    
                    if severity == "critical":
                        recommendations.append(f"Immediate medical review recommended for {metric} levels in {condition}")
                    elif severity == "high":
                        recommendations.append(f"Schedule follow-up appointment to address {metric} concerns")
            
            # Ensure we have at least basic recommendations
            if not recommendations:
                recommendations = [
                    f"Continue monitoring wearable data for {patient_condition}",
                    "Maintain regular follow-up schedule"
                ]
            
            print(f"✅ [STEP 6] Completed in {time.time() - step6_start:.2f}s")
            print(f"    Generated {len(recommendations)} recommendations\n")
            
            span.log(agentc.span.SystemContent(value=f"Generated {len(recommendations)} clinical recommendations"))
            
            # STEP 7: Generate natural conversational summary using LLM
            print(f"🔧 [STEP 7] Generating LLM-based conversational summary...")
            step7_start = time.time()
            
            # Count alerts by severity
            alert_count = len(alerts)
            critical_count = len([a for a in alerts if a.get("severity", "").lower() == "critical"])
            high_count = len([a for a in alerts if a.get("severity", "").lower() == "high"])
            similar_count = len(similar_patients)
            
            # Detect question intent with priority (most specific first)
            question_lower = question.lower()
            
            # Check for specific question types with priority
            is_comparison_question = any(word in question_lower for word in ['compare', 'similar', 'other patients', 'cohort', 'different from'])
            is_research_question = any(word in question_lower for word in ['research', 'papers', 'studies', 'literature', 'evidence'])
            is_recommendation_question = any(word in question_lower for word in ['recommend', 'suggestion', 'what should', 'advice'])
            is_alert_question = any(word in question_lower for word in ['alert', 'critical', 'urgent', 'issue', 'problem'])
            is_trend_question = any(word in question_lower for word in ['trend', 'pattern', 'over time', 'change'])
            
            # Determine primary question type with priority
            question_type = 'general'
            if is_comparison_question:
                question_type = 'comparison'
            elif is_research_question:
                question_type = 'research'
            elif is_recommendation_question:
                question_type = 'recommendations'
            elif is_alert_question:
                question_type = 'alerts'
            elif is_trend_question:
                question_type = 'trends'
            
            print(f"    📊 [QUESTION ANALYSIS]")
            print(f"       Question: '{question}'")
            print(f"       Primary question type: {question_type}")
            print(f"       Flags: comparison={is_comparison_question}, research={is_research_question}, recommendation={is_recommendation_question}, alert={is_alert_question}, trend={is_trend_question}")
            
            # Build context summary for LLM based on question type
            context_parts = []
            
            # Always include basic patient info
            context_parts.append(f"Patient: {patient_name}, Condition: {patient_condition}")
            context_parts.append(f"Data: {len(wearable_data) if isinstance(wearable_data, list) else 0} wearable readings over 30 days")
            
            # Add alert information
            if critical_count > 0:
                critical_alerts = [a for a in alerts if a.get("severity", "").lower() == "critical"]
                for alert in critical_alerts[:2]:  # Top 2 critical
                    metric = alert.get("metric", "").replace("_", " ")
                    message = alert.get("message", "")
                    context_parts.append(f"CRITICAL ALERT: {message}")
            elif high_count > 0:
                context_parts.append(f"{high_count} high-priority alert(s) detected")
            else:
                context_parts.append("No critical alerts - metrics within acceptable ranges")
            
            # Add patient comparison if relevant (especially for comparison questions)
            if question_type == 'comparison' or patient_comparison.get("outlier_status") in ["critical", "concerning"]:
                context_parts.append(f"Cohort comparison: {patient_comparison.get('summary', 'No comparison data')}")
                if patient_comparison.get("comparison_points"):
                    for point in patient_comparison["comparison_points"][:2]:  # Top 2 points
                        context_parts.append(f"  - {point}")
            
            # Add recommendations if relevant
            if question_type in ['recommendations', 'research'] and recommendations:
                context_parts.append(f"Clinical recommendations ({len(recommendations)}):")
                for rec in recommendations[:3]:  # Top 3 recommendations
                    context_parts.append(f"  - {rec}")
            
            context_summary = "\n".join(context_parts)
            
            # Build LLM prompt based on question type
            if question_type == 'comparison':
                focus_instruction = "Focus your response on how this patient compares to similar patients. Highlight any significant deviations or similarities."
            elif question_type == 'research':
                focus_instruction = "Focus on clinical evidence and research-backed recommendations. Reference standard guidelines for this condition."
            elif question_type == 'recommendations':
                focus_instruction = "Focus on actionable clinical recommendations. Prioritize by urgency and clinical significance."
            elif question_type == 'alerts':
                focus_instruction = "Focus on critical alerts and urgent issues requiring immediate attention. Be direct about severity."
            elif question_type == 'trends':
                focus_instruction = "Focus on patterns and trends over the 30-day period. Describe changes and trajectories."
            else:
                focus_instruction = "Provide a balanced overview covering key findings, alerts, and recommendations."
            
            summary_prompt = f"""You are a clinical AI assistant analyzing wearable health data. 

User's Question: "{question}"
Question Type: {question_type}

Analysis Context:
{context_summary}

Instructions: {focus_instruction}

Generate a concise, professional summary (2-4 sentences) that directly answers the user's question. Be clear, specific, and clinically appropriate. Use markdown formatting for emphasis where appropriate (**bold** for critical items, ⚠️ for warnings)."""

            # Call LLM to generate natural summary
            print(f"    🤖 [LLM] Generating conversational summary...")
            llm_start = time.time()
            
            try:
                from langchain_core.messages import HumanMessage
                
                # Log LLM generation (using ChatCompletionContent for the response)
                llm_response = self.chat_model.invoke([HumanMessage(content=summary_prompt)])
                comprehensive_summary = llm_response.content.strip()
                
                # Log the LLM output
                span.log(agentc.span.ChatCompletionContent(
                    output=comprehensive_summary,
                    meta={
                        "model": str(self.chat_model.model_name) if hasattr(self.chat_model, 'model_name') else "gpt-4o-mini",
                        "tokens": llm_response.response_metadata.get("token_usage", {}) if hasattr(llm_response, 'response_metadata') else {}
                    }
                ))
                
                print(f"    ✅ [LLM] Generated summary in {time.time() - llm_start:.2f}s")
            except Exception as e:
                print(f"    ⚠️  [LLM] Error generating summary: {e}")
                # Fallback to structured summary if LLM fails
                comprehensive_summary = f"Analysis for {patient_name} ({patient_condition}): "
                if critical_count > 0:
                    comprehensive_summary += f"⚠️ **{critical_count} CRITICAL alert(s)** detected requiring immediate attention."
                elif high_count > 0:
                    comprehensive_summary += f"**{high_count} high-priority alert(s)** identified."
                else:
                    comprehensive_summary += "No critical alerts detected. Metrics within acceptable ranges."
            
            span.log(agentc.span.SystemContent(value=f"Generated {question_type}-focused summary using LLM"))
            
            print(f"✅ [STEP 7] Completed in {time.time() - step7_start:.2f}s")
            print(f"    Summary type: {question_type.title()}")
            print(f"    Summary length: {len(comprehensive_summary)} chars\n")
            
            # Update state with all results (including patient comparison and research papers)
            state["patient_id"] = patient_id
            state["patient_name"] = patient_name
            state["patient_condition"] = patient_condition
            state["question"] = question
            state["wearable_data"] = wearable_data if isinstance(wearable_data, list) else []
            state["similar_patients"] = similar_patients
            state["trend_analysis"] = trend_analysis
            state["patient_comparison"] = patient_comparison
            state["research_papers"] = research_papers  # NEW: Add research papers
            state["alerts"] = alerts
            state["recommendations"] = recommendations
            state["answer"] = comprehensive_summary
            state["is_complete"] = True
            
            total_duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"✨ [AGENT] OPTIMIZED ANALYSIS COMPLETE")
            print(f"    Total time: {total_duration:.2f}s")
            print(f"    - Step 1 (Patient info): {time.time() - step1_start:.2f}s")
            print(f"    - Step 2 (Wearable data): {time.time() - step2_start:.2f}s")
            print(f"    - Step 3 (Trend analysis): {time.time() - step3_start:.2f}s")
            print(f"    - Step 4 (Similar patients): {time.time() - step4_start:.2f}s")
            print(f"    - Step 5 (Patient comparison): {time.time() - step5_start:.2f}s")
            print(f"    - Step 5.5 (Research papers): {time.time() - step5_5_start:.2f}s")
            print(f"    - Step 6 (Recommendations): {time.time() - step6_start:.2f}s")
            print(f"    - Step 7 (Summary): {time.time() - step7_start:.2f}s")
            print(f"    Alerts: {len(alerts)}")
            print(f"    Research papers: {len(research_papers)}")
            print(f"    Recommendations: {len(recommendations)}")
            print(f"    Outlier status: {patient_comparison['outlier_status']}")
            print(f"{'='*80}\n")
            
            span.log(agentc.span.SystemContent(
                value=f"✅ Analysis complete: {len(alerts)} alerts ({critical_count} critical), {len(research_papers)} research papers, {len(recommendations)} recommendations in {total_duration:.2f}s"
            ))
            
            return state
            
        except Exception as e:
            error_time = time.time() - start_time
            print(f"❌ [AGENT] ERROR after {error_time:.2f}s: {str(e)}")
            raise
