# Soul Explorer Bot - Workflow

## Workflow

### Step 1: Entry Point
This is the entry to the soul journey. You can type "start" or "custom" to begin your soul exploration!

### Step 2: Process Options
There are two different processes:
1. Directly generate a script
2. Ask the tester for scene and setting: "What scene, plot style, and character do you want?"

| User Input | Action |
|------------|--------|
| "start"    | ✅ Randomly generate plot + random character, immediately enter the plot process |
| "custom"   | ✅ Enter custom setting process, user inputs scene and character |
| Other (e.g., empty or random input) | ❌ Output "You can always come back to start your soul journey." and exit |

### Step 3: Core Process
Custom/Direct generation → Scene A → Choice → Scene B → Choice → ... (can loop) → Final scene (ending) → Final soulmate analysis (about 200 words in paragraph form)

### Process Overview

#### How to Start
- The bot acts as the "entry to the soul journey"
- The user can enter "start" or "custom" to begin soul exploration

#### Random Module Integration
- Use the `random` module to support "inspiration generation"

#### Vocabulary Fragment Pool Creation
- Prepare three types of text fragments: adjectives, nouns, verbs
- For example: "floating" (adjective/verb), "soul" (noun), "traverse" (verb)

#### User Entry Point Selection
- **Input "start"**: Automatically generate scene and character
- **Input "custom"**: Allow user to manually input scene and character
- **Other input**: The bot ends the current interaction and prompts the user: "You can always come back to start your soul journey. You can type 'start' or 'custom' to begin your soul exploration!"

#### Initialization State
- Set total chapters to 5
- Start from chapter 1
- Initialize an empty list called `user_choices` to record user choices

#### Story Loop (within 5 scenes)
- **Micro-story generation**: Each scene generates a "micro-story" less than or equal to 150 characters
- **Behavioral options**: The bot provides four behavioral options, labeled A to D, for the user to choose
- **Story progression**: After the user makes a choice, record it and advance the story accordingly

#### Story Ending
- **Do not provide A~D behavioral options**
- **Do not output "Please choose your next action" or similar prompts**
- **Ending content must not contain any options or prompts**
- **Only output the complete story ending and soulmate analysis text** (≤150 characters)

#### Ending Analysis
- **Determine soulmate type based on the most frequently chosen option** (Explorer/Logical/Emotional/Fate)

#### Output result and end
- **Show soulmate analysis**
- **Do not output any options or prompts** 