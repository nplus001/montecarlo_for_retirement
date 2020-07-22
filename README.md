# Monte Carlo Simulation for Retirement Planning
This repository is created to publicly share the Line Bot for retirement planning using monte carlo simulation written in Python. To run the script, Line Messaging API channel for your bot needs to be created.

## Documentation
Following document will guide you through the process of creating a Line Bot with Python. You will need a **channel access token** and a **channel secret** as an input to the script.

Getting Started with Line Messaging API
https://developers.line.biz/en/docs/messaging-api/getting-started/#using-console

Building a Line Bot
https://developers.line.biz/en/docs/messaging-api/building-bot/

Line Messaging API SDK for Python
https://github.com/line/line-bot-sdk-python
 

## Requirements
Python >= 3.4 and other libraries as specified in requirements.txt

## Usage 
Edit line_bot_finance.py and put your channel access token and channel secret in the following lines. 
```python
line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_VHANNEL_SECRET')
```
Run the Python script.
```cmd
python line_bot_finance.py
```
Add your Line Official Account and test your the simulation.
