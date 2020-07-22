#!/usr/bin/env python
# -*- coding: utf-8 -*-
# coding: utf-8

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, UnfollowEvent
import numpy as np
import json
import ast

app = Flask(__name__)

secrets = json.load(open('secrets.json'))

line_bot_api = LineBotApi(secrets["line_access_token"])
handler = WebhookHandler(secrets["webhook_handler"])

def simple_cash_required_at_retirement(years_after_retirement, spending_per_month_now):
    """
    Calculate a simple cash required at retirement 
    """
    cash = years_after_retirement * 12 * spending_per_month_now
    
    return cash 

def get_inflation_and_investment_profile(age, retirement_age, years_after_retirement, num_sim,
                                        inf_assumptions=(0.015,0.01),
                                        int_assumptions=(0.03,0.1)
                                        ):
    
    months_before_retirement = (retirement_age - age) * 12
    months_after_retirement = years_after_retirement * 12
    
    ann_inf = (np.random.randn(num_sim, months_before_retirement + months_after_retirement) * inf_assumptions[1] + inf_assumptions[0])/12
    ann_int = (np.random.randn(num_sim, months_before_retirement + months_after_retirement) * int_assumptions[1] + int_assumptions[0])/12
    
    return ann_inf, ann_int
    
def fv_cash_required_at_retirement(age, retirement_age, years_after_retirement, spending_per_month_now, 
                                   ann_inf, ann_int):

    """
    Calculate a future cash required at retirement 
    """
    months_before_retirement = (retirement_age - age) * 12
    months_after_retirement = years_after_retirement * 12
    
    # inflation from retirement til the last day
    inflation_mlp_after_retirement_arr = np.cumproduct(1 + ann_inf, axis=1)[:,months_before_retirement:]
    
    # interest from retirement til the last day
    ann_int = ann_int[:,months_before_retirement:]
    interest_mlp_after_retirement_arr = np.cumproduct(1 + ann_int, axis=1)
    
    # spending now to future value
    fv_monthly_spending = inflation_mlp_after_retirement_arr * spending_per_month_now
    
    # discount back to value at retirement
    values_at_retirement = fv_monthly_spending / interest_mlp_after_retirement_arr
    pv_at_retirement = np.sum(values_at_retirement, axis=1)
    
    return pv_at_retirement


def get_monthly_saving(age, retirement_age, retirement_saving_goal, ann_int, annual_saving_growth):
    """
    Given a constant of target cash at retirement, calculate a fix saving per month
    """
    months_before_retirement = (retirement_age - age) * 12
    
    # investment before retirement
    ann_int = ann_int[:,:months_before_retirement]
    interest_mlp_after_retirement_arr = np.cumproduct(1 + ann_int, axis=1)
    
    ## solve for constant saving per month 
    """
    retirement_saving_goal = sum(distcount_factors_array * saving_per_month_now)
    retirement_saving_goal = sum(distcount_factors_array) * saving_per_month_now
    """ 
    saving_per_month = retirement_saving_goal / np.sum(interest_mlp_after_retirement_arr, axis=1)
    
    # growth factor
    num_sim = ann_int.shape[0]
    saving_growth_multipliers = np.repeat(np.cumproduct(np.ones(shape=(num_sim, np.int(months_before_retirement/12) )) * (1 + annual_saving_growth), axis=1), 12,axis=1)
    
    saving_first_month = retirement_saving_goal / np.sum(interest_mlp_after_retirement_arr * saving_growth_multipliers, axis=1)
    growth_saving = np.repeat(saving_first_month.reshape(len(saving_first_month),1), months_before_retirement,axis=1) * saving_growth_multipliers
    
    return saving_per_month, growth_saving

def get_event_component(event):
	# Line event to dict 
    event_str = str(event)
    event_dict = ast.literal_eval(event_str)

    # Body
    user_id = event_dict['source']['userId']
    action = event_dict['type']
    ts = event_dict['timestamp'] #int
    try:
        message = event_dict['message']['text']
    except:
        message = ''

    return user_id, action, ts, message

@app.route("/callback", methods=['POST'])
def callback():
	# get X-Line-Signature header value
	signature = request.headers['X-Line-Signature']

	# get request body as text
	body = request.get_data(as_text=True)
	app.logger.info("Request body: " + body)

	# handle webhook body
	try:
		handler.handle(body, signature)
	except InvalidSignatureError :
		print("Invalid signature. Please check your channel access token/channel secret")
		abort(400)

	return 'OK'


# inputs
user = dict()

# initial settings
#age, retirement_age, years_after_retirement, spend_per_month_in_pv = 25, 65, 20, 20000
#inf_assumptions = (0.01, 0.01)
#inv_assumptions = (0.03, 0.05)
#num_sim = 1000

@handler.add(FollowEvent)
def add_user(event):
    
    global user
    # add user dict
    user[event.source.user_id] = dict()

@handler.add(UnfollowEvent)
def user_unfollow(event):
    print("unfollow")
    print(event)

# a function to receive and reply message
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

	global user

	# use variable active_reply from outside function
	#global age, retirement_age, years_after_retirement, spend_per_month_in_pv, inf_assumptions, inv_assumptions, num_sim

	# clean message
	received_msg = event.message.text
	received_msg_l = received_msg.replace(" ","").lower()

	# reply
	if 'profile' in received_msg_l:
		_, profile_text = received_msg_l.split('=')
		age, retirement_age, years_after_retirement, spend_per_month_in_pv = list(np.array(profile_text.split(',')).astype('int'))

		user[event.source.user_id]['age'] = age
		user[event.source.user_id]['retirement_age'] = retirement_age
		user[event.source.user_id]['years_after_retirement'] = years_after_retirement
		user[event.source.user_id]['spend_per_month_in_pv'] = spend_per_month_in_pv

		line_bot_api.reply_message(event.reply_token, TextMessage(text="Next, please specify your investment assumptions."))

	elif 'assumptions' in received_msg_l:
		_, assumptions_text = received_msg_l.split('=')
		inv_mean, inv_std = assumptions_text.split(',')
		
		user[event.source.user_id]['inv_mean'] = inv_mean
		user[event.source.user_id]['inv_std'] = inv_std

		line_bot_api.reply_message(event.reply_token, TextMessage(text="You can adjust your profile and assumptions by resending messages. Once you're ready, type 'run' to start the simulation"))

	elif 'run' in received_msg_l:
		
		# stay in active mode
		active_reply = True

		# get user data
		try:
			print(user)
			age = user[event.source.user_id]['age']
			retirement_age = user[event.source.user_id]['retirement_age']
			years_after_retirement = user[event.source.user_id]['years_after_retirement']
			spend_per_month_in_pv = user[event.source.user_id]['spend_per_month_in_pv']
			inv_assumptions = (np.float(user[event.source.user_id]['inv_mean']),np.float(user[event.source.user_id]['inv_std']))
			inf_assumptions = (0.02,0.01)
			num_sim = 1000
		except:
			line_bot_api.reply_message(event.reply_token, TextMessage(text="You need to specify your profile and assumptions"))
			raise ValueError('Cannot find user data')

		ann_inf, ann_int = get_inflation_and_investment_profile(age, retirement_age, years_after_retirement, num_sim, inf_assumptions, inv_assumptions)

		fv_profiles = fv_cash_required_at_retirement(age, retirement_age, years_after_retirement, spend_per_month_in_pv, ann_inf, ann_int)

		retirement_saving_goal = f'{int(round(np.percentile(fv_profiles, 95), -5)):,}'

		# saving
		constant_saving, growth_saving = get_monthly_saving(age, retirement_age, fv_profiles, ann_int, annual_saving_growth=0.05)
		
		constant_saving_95 = f'{int(round(np.percentile(constant_saving, 95),-2)):,}'
		start_saving_95 = f'{int(round(np.percentile(growth_saving[:,0], 95),-2)):,}'

		# reply
		line_bot_api.reply_message(event.reply_token, TextMessage(text="You will need {0} at your retirement date. ".format(retirement_saving_goal) +
			"From now until your retirement, you can either save a fix amount of {0} per month or start with {1} per month now and increase it by 5% per year in order to reach your goal.".format(constant_saving_95,start_saving_95)))

if __name__ == "__main__":
	app.run()