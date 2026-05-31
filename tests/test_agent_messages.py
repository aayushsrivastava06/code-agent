import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.context import ConversationContext
from agent.config import Config
from agent.core import Agent


def test_build_messages_includes_tool_calls():
    ctx = ConversationContext('.')
    cfg = Config()
    agent = Agent(cfg, ctx)
    ctx.add_user_message('hi')
    ctx.add_assistant_message('', tool_calls=[{'id':'1','name':'do', 'arguments':{}}])
    msgs = agent._build_messages_for_api()
    # Assistant message should include a readable placeholder for tool calls
    assistant_msgs = [m for m in msgs if m.get('role') == 'assistant']
    assert assistant_msgs, 'no assistant messages built'
    assert any(m.get('content', '').startswith('[tool_calls]') for m in assistant_msgs)
