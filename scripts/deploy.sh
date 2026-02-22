#!/bin/bash

echo "Starting Deployment to Google Cloud Run (foundtel project)..."

# Load the environment variables to securely pass them to Cloud Run
if [ -f ../.env ]; then
  set -a
  source ../.env
  set +a
else
  echo "Error: .env file not found. Deployment cannot proceed."
  exit 1
fi

gcloud run deploy foundtel-onboarding \
  --source . \
  --project foundtel \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --quiet \
  --set-env-vars="MONGODB_URL=$MONGODB_URL,GOOGLE_API_KEY=$GOOGLE_API_KEY,TINYFISH_API_KEY=$TINYFISH_API_KEY,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET,TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN,TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER"

echo "------------------------------------------------------"
echo "Deployment Complete!"
echo "To finish Phase 6, copy your new Cloud Run Service URL from above."
echo "Then, create the daily 7:00 AM Cron Job by running this command in your terminal:"
echo ""
echo 'gcloud scheduler jobs create http default-daily-briefs \'
echo '  --schedule="0 7 * * *" \'
echo '  --uri="YOUR_NEW_CLOUD_RUN_URL/trigger-briefs" \'
echo '  --http-method=POST \'
echo '  --headers="Authorization=Bearer foundtel-cron-secret-123" \'
echo '  --time-zone="America/Los_Angeles" \'
echo '  --location="us-central1"'
echo "------------------------------------------------------"
