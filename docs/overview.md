# AI Operations Agent - Business Overview

The [solution design diagrams](designs/README.md) show the implemented architecture and workflows. Supporting technical choices are recorded in the [Architecture Decision Records](adrs/README.md), and the delivery work is mapped in the [Implementation Task Map](tasks/README.md).

## Purpose

The proposed solution is an AI Operations Agent that helps bank advisors understand why a transaction has been held and what should happen next.

An advisor will be able to ask a question such as:

> Why is transaction TXN-0212 held?

The agent will look up the transaction, review the relevant internal procedure, and provide a clear explanation and recommended next step. It will support the advisor's investigation rather than approve, release, reject, or change a transaction.

## The problem it solves

When a transaction is held, an advisor may need to consult several systems and procedures before they can explain the situation or refer it to the correct team. This can be slow and inconsistent.

The agent brings the relevant information together in one response. It is intended to:

- reduce the time needed to understand a held transaction;
- provide consistent guidance based on approved procedures;
- make it clear when another team or a human decision-maker must be involved; and
- avoid guessing when information is missing or unavailable.

## What needs to be built

### 1. A simple advisor interface

Create a command-line application where an advisor can enter a transaction-related question. A command-line interface keeps the prototype quick to build and easy to demonstrate without spending time on a polished front end.

### 2. A transaction lookup

Create a small set of fictional transactions for the demonstration. Each transaction should include basic information such as:

- transaction status;
- amount and currency;
- risk level;
- reason for the hold; and
- transaction channel.

The agent must use this information when answering. It must not invent transaction details.

### 3. A small procedure library

Create four short, fictional bank procedures covering common reasons for a transaction hold:

1. Sanctions screening
2. High-value or unusual transaction activity
3. Beneficiary information that is missing or does not match
4. Manual review and escalation

These documents will form the agent's reference library. The answer should identify which procedure was used so the advisor can see where the guidance came from.

### 4. A local AI model

Use the Qwen 3.5 9B model through Ollama to write a short, natural-language explanation from the verified transaction and procedure information.

The AI model should only explain the available evidence. Business rules, escalation decisions, and permitted actions should remain controlled by the application.

### 5. A controlled investigation process

The agent should follow the same sequence for every investigation:

1. Check that the request is about a transaction and contains one valid transaction number.
2. Look up the transaction.
3. Find the most relevant procedure.
4. Determine whether the matter requires human review or escalation.
5. Ask the AI model to present the verified information clearly.
6. Check the answer before showing it to the advisor.

This gives the benefits of AI-generated explanations without allowing the model to control operational decisions.

## Expected response

Every successful investigation should clearly show:

- the transaction number and current status;
- why the transaction is held;
- the relevant procedure;
- the recommended next action;
- whether human review or escalation is required; and
- the team that should receive the case, where applicable.

For example, the agent may explain that `TXN-0212` is held because the beneficiary details do not match, refer to the beneficiary-verification procedure, and advise the user to confirm the details before referring the case to Payments Operations.

## Safety and failure handling

The agent must respond safely when it cannot provide a reliable answer.

| Situation | Expected response |
| --- | --- |
| No transaction number is provided | Ask the advisor for a valid transaction number |
| The transaction cannot be found | State that it was not found without guessing why |
| Transaction information is unavailable | Advise the user to retry or refer the case to Operations |
| No relevant procedure can be found | Escalate the case for human review |
| The AI model is unavailable | Provide a simple response using the verified facts and procedure |
| The request asks the agent to release or alter a transaction | Explain that the agent is advisory and cannot perform the action |

The agent should always choose a cautious response when the information is incomplete or uncertain.

## Demonstration scenarios

The prototype should demonstrate three scenarios:

### Successful investigation

The advisor asks about `TXN-0212`. The agent finds the held transaction, identifies the matching procedure, explains the hold, and recommends the appropriate referral.

### Transaction not found

The advisor asks about an unknown transaction. The agent states that it cannot find the transaction and does not create an explanation from incomplete information.

### AI service unavailable

The local AI model is stopped. The agent still returns a safe, basic response using the transaction facts and procedure guidance.

## Delivery plan

### Step 1 - Prepare the example information

- Create the fictional transaction records.
- Write the four short procedures.
- Make `TXN-0212` the main demonstration case.

### Step 2 - Build the investigation process

- Accept a question from the command line.
- Look up the transaction.
- Find the relevant procedure.
- Decide when human review is required.

### Step 3 - Add the AI explanation

- Connect the local Qwen model.
- Give it only the verified transaction and procedure information.
- Ensure the response follows the required format.

### Step 4 - Add safe failure responses

- Handle missing and unknown transaction numbers.
- Handle unavailable transaction information.
- Handle missing procedures and an unavailable AI model.

### Step 5 - Test and document the demonstration

- Test the successful and failure scenarios.
- Add short setup and usage instructions.
- Prepare the commands and talking points for the technical walkthrough.

## What will be delivered

- A working command-line prototype
- Four fictional procedure documents
- A small set of fictional transaction records
- A searchable procedure library
- A structured and readable investigation response
- Automated checks for the most important business rules and failure scenarios
- A README explaining how to set up, run, and demonstrate the solution

## Measures of success

The prototype will be successful when:

- an advisor can investigate `TXN-0212` with one command;
- the response correctly uses the fictional transaction information;
- the response identifies the relevant procedure and next step;
- held or high-risk transactions are always referred for human review;
- unknown transactions and missing information produce safe responses;
- the solution continues to provide basic guidance if the AI model is unavailable; and
- a reviewer can run the demonstration using the README.

## Future development

If the prototype were developed for real banking use, the fictional transaction records would be replaced by a secure, read-only connection to the bank's systems. The procedure library would be governed and kept up to date, access would be limited by employee role, sensitive information would be protected, and every investigation would be recorded for audit purposes.

The AI model could also be moved from the local demonstration environment to the bank's approved Oracle Cloud environment without changing the advisor experience.
