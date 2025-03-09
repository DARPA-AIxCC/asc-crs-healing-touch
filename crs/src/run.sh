#! /bin/bash

printf "Starting Healing Touch Orchestrator Instance\n"
python3 /app/orchestrator/server.py &

name="$(hostname)-{$RANDOM}"

until curl "${HEALING_TOUCH_BACKEND}/health/" >/dev/null; do
	printf "Waiting for the Backend to be available...\n"
	sleep 5
	((c++)) && ((c == 12)) && exit 1 #TODO change to failsafe instead of exit
done

printf "Run health check before we get started.\n\n"
(
	set -x
	curl "${HEALING_TOUCH_BACKEND}/health/"
) | jq


printf "Get next subject to work on.\n\n"

has_subject(){
  # Execute the curl command and store the result
  local response=$(curl "${HEALING_TOUCH_BACKEND}/has_subject/")
    # Check if the curl command was successful
  if [ $? -ne 0 ]; then
    echo "Error executing curl command"
    return 1
  fi


    # Use jq to parse the JSON and extract the variables
  local variable1=$(echo "$response" | jq -r '.status')

  if [[ $variable1 == "YES" ]];
  then
    return 1
  else
    return 0;
  fi
}


cd "/app/orchestrator"

# Ensure AFLplusplus and jacoco can be used for building if needed
# cp -rf /app/AFLplusplus ${AIXCC_CRS_SCRATCH_SPACE}/AFLplusplus

export COLUMNS=800

if [[ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]];
then
      # Use jq to parse the JSON and extract the variables
  export PROJECT_ID=$(jq -r '.project_id' $GOOGLE_APPLICATION_CREDENTIALS)
  export PRIVATE_KEY_ID=$(jq -r '.private_key_id' $GOOGLE_APPLICATION_CREDENTIALS)
  export PRIVATE_KEY=$(jq -r '.private_key' $GOOGLE_APPLICATION_CREDENTIALS)
  export CLIENT_EMAIL=$(jq -r '.client_email' $GOOGLE_APPLICATION_CREDENTIALS)
  export CLIENT_ID=$(jq -r '.client_id' $GOOGLE_APPLICATION_CREDENTIALS)
  export CLIENT_CERT=$(jq -r '.client_x509_cert_url' $GOOGLE_APPLICATION_CREDENTIALS)
fi



cat <<EOF > /app/orchestrator/config/api.json
{
  "openai_token": "${OPENAI_API_KEY}",
  "azure_token": "${AZURE_API_KEY}",
  "azure_base": "${AZURE_API_BASE:-https://aicc.openai.azure.com}",
  "anthropic_token": "${ANTHROPIC_API_KEY}",
  "huggingface_token": "",
  "gemini_token": {
    "project_id": "${PROJECT_ID}",
    "private_key_id": "${PRIVATE_KEY_ID}",
    "private_key": "${PRIVATE_KEY}",
    "client_email": "${CLIENT_EMAIL}",
    "client_id": "${CLIENT_ID}",
    "client_x509_cert_url": "${CLIENT_CERT}"
  }
}
EOF


# Ensure that no weird behavior happens due to git repos
git config --global --add safe.directory '*'


CPU_COUNT=`nproc`


if [[ $HT_DEV_MODE == 1 ]];
then
    while true; 
    do
        echo "Sleeping for Dev mode" 
        sleep 5; 
    done
else
    while true; 
    do
        # Execute the curl command and store the result
        response=$(curl "${HEALING_TOUCH_BACKEND}/next_subject/" --header "Content-Type: application/json" --request POST --data "{\"id\":\"${name}\"}")

        # Check if the curl command was successful
        if [ $? -ne 0 ]; then
          echo "Error executing curl command"
          sleep 10
          continue
        fi

        echo "Response is $response"

        # Use jq to parse the JSON and extract the variables
        SUBJECT_NAME=$(echo "$response" | jq -r '.subject')
        BUG_ID=$(echo "$response" | jq -r '.bug_id')
        CPU_COUNT=$(echo "$response" | jq -r '.cpus')
        SUBJECT_ID=$(echo "$response" | jq -r '.subject_name')


        printf "Subject ${SUBJECT_NAME}.\n\n"
        printf "Subject DIR ${SUBJECT_ID}.\n\n"
        printf "Bug ID ${BUG_ID}.\n\n"
        printf "CPUs ${CPU_COUNT}.\n\n"
        
        # Check if jq was successful in extracting the variables
        if [ -z "$SUBJECT_NAME" ] || [ -z "$SUBJECT_ID" ] || [ -z "$BUG_ID" ] || [ -z "$CPU_COUNT" ] || [[ "$SUBJECT_NAME" == "null" ]] || [[ "$SUBJECT_ID" == "null" ]]  || [[ "$BUG_ID" == "null" ]] || [[ "$CPU_COUNT" == "null" ]] ; then
          echo "No data passed. Sleeping a little"
          sleep 10
          continue
        fi

        
        echo "Waiting for ${AIXCC_CRS_SCRATCH_SPACE}/benchmark/darpa/${SUBJECT_NAME}/${SUBJECT_ID}/.prepared"

        until [ -f "${AIXCC_CRS_SCRATCH_SPACE}/benchmark/darpa/${SUBJECT_NAME}/${SUBJECT_ID}/.prepared" ];
        do 
            ls ${AIXCC_CRS_SCRATCH_SPACE}/benchmark/darpa/${SUBJECT_NAME}/;
            echo "Sleeping for preparation"
            sleep 10;
        done

        echo "READY!"
        workflow_name="${AIXCC_CRS_SCRATCH_SPACE}/benchmark/darpa/${SUBJECT_NAME}/workflow-${BUG_ID}-$((1 + $RANDOM % 100000)).json"
        cp "${AIXCC_CRS_SCRATCH_SPACE}/benchmark/darpa/${SUBJECT_NAME}/workflow.json" ${workflow_name}

        sed -i "s/\"\\*\"/\"${BUG_ID}\"/" ${workflow_name}
        sed -i -r "s/\"cpu(s|-count)\": 6/\"cpu\1\": ${CPU_COUNT}/" ${workflow_name}

        timeout -k 5m 4h python3 -m main \
            -c $workflow_name \
            --special-meta="${AIXCC_CRS_SCRATCH_SPACE}/benchmark/darpa/${SUBJECT_NAME}/meta-data.json" &

        sleep $((1 + $RANDOM % 5))
    done
fi
