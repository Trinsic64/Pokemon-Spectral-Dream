# DSPRE Scene Template Library

Expanded HGSS template library for Scene Editor script assembly.

## Scope

- Root folder: `Documents/Script-Docs/Template-Scripts`
- Template count: **50**
- Category count: **13**

## Categories

### 01-Greeting
- ArchiveGreeting.json
- BasicGreeting.json
- DialogueGreeting.json
- FlagConditionalGreeting.json
- SilentGreetingNoFace.json

### 02-Dialogue
- MultiBranchDialogue.json
- SimpleDialogue.json

### 03-ConditionalLogic
- CompareFlagAndJump.json
- CompareVarAndBranch.json
- NestedBranch.json

### 04-ItemLogic
- CheckItemSpace.json
- GiveItem.json
- GiveItemWithFlag.json

### 05-Movement
- BasicWalk.json
- MovementWithBranch.json
- PatrolSequence.json

### 06-CommonScripts
- BagFullCommonScript.json
- CommonScriptCall.json
- GiveItemVerboseCommonScript.json
- SignpostCommonScript.json
- YesNoPrompt.json

### 07-FlowControl
- CallFunction.json
- CallIfCondition.json
- JumpFunction.json
- JumpIfCondition.json
- LocalScriptEnd.json
- ReturnFunction.json

### 08-VisualAudio
- FadeOutIn.json
- FadeWarpFadeIn.json
- PlayFanfareThenMessage.json
- PlaySoundAndWait.json
- ShakeCameraCue.json

### 09-Pokemon
- ChoosePokemonAndCheckMove.json
- GivePokemonGift.json
- HealPartyInteraction.json
- PartyNicknameDialogue.json

### 10-Overworld
- AddOverworldIfFlagUnset.json
- GetOwPositionBranch.json
- RemoveOverworldIfFlagSet.json
- SetOwMovementType.json

### 11-TextAndBoards
- BoardMessageInteraction.json
- MessageFromCommonArchive.json
- PlayerNameMessage.json
- TextItemMessage.json
- TextNumberMessage.json

### 12-WarpAndTransition
- BasicWarp.json
- FadeWarp.json
- ReturnScreenWrapper.json

### 99-Misc
- CustomUnknownPattern.json
- RawActionSnippet.json

## Format

- metadata (`templateId`, `name`, `description`, `category`)
- typed parameters and validation hints
- scene block mapping hints
- scriptModel containers with command lines

## Sources

- `Tools/DSPRE/DS_Map/Editors/Utils/SceneBlockCatalog.cs`
- `Tools/DSPRE/DS_Map/Editors/Utils/SceneBlockCompiler.cs`
- `Tools/DSPRE/DS_Map/Editors/Utils/SceneBlockParser.cs`
- `Data/Script-Data/SCRCMD Database - HGSS.csv`
- `Data/Script-Data/SCRCMD Database - Actions.csv`
- `Data/Script-Data/Scripts/*.script`
