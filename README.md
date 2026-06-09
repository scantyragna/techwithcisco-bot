# TechWithCisco Bot — Render Deployment Guide

## Step 1: Revoke and get new bot token
1. Open Telegram → search @BotFather
2. Type /mybots → select your bot
3. Tap API Token → Revoke → copy new token

## Step 2: Push to GitHub
1. Go to github.com → sign up / log in
2. Click "New repository" → name it: techwithcisco-bot
3. Upload these 3 files: bot.py, requirements.txt, README.md
4. Click "Commit changes"

## Step 3: Deploy on Render
1. Go to render.com → sign up free
2. Click "New" → "Web Service"
3. Connect your GitHub account → select techwithcisco-bot repo
4. Fill in these settings:
   - Name: techwithcisco-bot
   - Runtime: Python
   - Build command: pip install -r requirements.txt
   - Start command: python bot.py
5. Add these environment variables:
   - BOT_TOKEN = (your new token from BotFather)
   - WEBHOOK_URL = https://techwithcisco-bot.onrender.com  ← Render gives you this URL
6. Click "Create Web Service"
7. Wait ~2 minutes for it to deploy

## Step 4: Get your Telegram community invite link
1. Open your Telegram community
2. Tap the name at the top → Edit → Invite Links
3. Create a new invite link → copy it
4. Paste it as the COMMUNITY_LINK environment variable on Render

## Your bot is now live 24/7!

## Admin commands (send to your bot on Telegram)
/report   → Full student list + revenue summary
/list     → All enrolled students
/list Monday → Students for a specific day
/pending  → Pending approvals with approve/reject buttons
/revenue  → Quick money summary

## How approvals work
1. Student submits transaction ID
2. You get instant Telegram notification
3. Tap ✅ Approve → student gets community link immediately
4. Tap ❌ Reject → student is asked to recheck and resubmit
