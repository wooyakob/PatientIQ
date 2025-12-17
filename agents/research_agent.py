#!/usr/bin/env python3
"""
Research Agent that searches, 
summarizes and delivers 
aligned medical research for a specific topic area.
"""
import json
import logging
import os
import sys
from datetime import timedelta

import agentc
import agentc_langgraph.agent
import agentc_langgraph.graph
import dotenv
import langchain_core.messages
import langchain_core.runnables
import langchain_openai.chat_models
import langgraph.graph
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.exceptions import KeyspaceNotFoundException
from couchbase.options import ClusterOptions
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from pydantic import SecretStr

class MedicalResearchState(agentc_langgraph.agent.State):
    """State for medical research conversations - single user system."""

    topic: str
    resolved: bool
    papers: list[dict]
    summary: str

class MedicalResearchAgent(agentc_langgraph.agent.ReActAgent):
    """Medical research agent using Agent Catalog tools and ReActAgent framework."""

    def __init__(
        self,
        catalog: agentc.Catalog,
        span: agentc.Span,
        chat_model=None,
        prompt_name: str = "simple_prompt",
    ):
        if chat_model is None:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            chat_model = langchain_openai.chat_models.ChatOpenAI(model=model_name, temperature=0.1)

        # call tools from agent: https://docs.couchbase.com/ai/build/integrate-agent-with-catalog.html#call
        self.hello_tool = catalog.find("tool", name="hello_tool")
        self.simple_prompt = catalog.find("prompt", name="simple_prompt")

        super().__init__(chat_model=chat_model, catalog=catalog, span=span, prompt_name=prompt_name)

