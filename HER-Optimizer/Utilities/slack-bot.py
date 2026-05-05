import slack

def send_message_to_slack(message):
    # Your Slack API token
    slack_token = "YOUR TOKEN"

    # Initialize a Slack client
    client = slack.WebClient(token=slack_token)

    # Define the channel where you want to send the message
    channel = "YOUR CHANNEL"

    # Send the message to Slack
    response = client.chat_postMessage(channel=channel, text=message)

    # Check if the message was sent successfully
    if response["ok"]:
        print("Message sent to Slack successfully.")
    else:
        print(f"Failed to send message to Slack. Error: {response['error']}")

if __name__ == "__main__":
    import sys

    # Extract the message from command line arguments
    message = "test".join(sys.argv[2:])

    # Send the message to Slack
    send_message_to_slack(message)