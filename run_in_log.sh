#!/bin/bash
LOG_FILE="run_data.log"
echo "" > $LOG_FILE
. ./lenv/bin/activate
python ./DiscordBot/src -d 2>&1 | tee -a $LOG_FILE
