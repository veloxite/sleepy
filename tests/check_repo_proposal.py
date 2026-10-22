"""Live model check only: prepares a proposal; never calls GitHub."""
from agent_core import Agent

if __name__ == '__main__':
    agent = Agent()
    agent.reply('Prepare a private GitHub repository named sleepy-demo with description Personal assistant experiment. Use the available proposal tool.', github=True)
    action = agent.pending_action
    assert action and action['name'] == 'sleepy-demo' and action['private'], 'Model did not prepare the expected proposal'
    print('PASS: Groq prepared a private repository review card. No GitHub request was made.')
