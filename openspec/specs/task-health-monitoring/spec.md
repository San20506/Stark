# Task: Health Monitoring Specification

## Overview
Monitor user wellbeing through camera-based posture detection, behavior tracking, and proactive health reminders.

**Priority**: High (practical daily use)  
**Trigger**: Continuous background monitoring + explicit queries

---

## Requirements

### Requirement: Posture Detection
The system SHALL monitor posture via camera and provide alerts.

#### Scenario: Bad posture detected
- **WHEN** user maintains poor posture for >5 minutes
- **THEN** send gentle reminder
- **AND** suggest correction

#### Scenario: Slouching alert
- **WHEN** significant slouching detected
- **THEN** provide specific posture tip
- **AND** track frequency for patterns

---

### Requirement: Break Reminders
The system SHALL remind users to take breaks.

#### Scenario: Screen time alert
- **WHEN** continuous screen time exceeds 50 minutes
- **THEN** suggest 10-minute break
- **AND** track daily screen time

#### Scenario: Eye strain prevention
- **WHEN** user hasn't looked away from screen
- **THEN** suggest 20-20-20 rule reminder
- **AND** dim suggestion if evening

---

### Requirement: Activity Tracking
The system SHALL track user activity patterns.

#### Scenario: Daily summary
- **WHEN** user asks for health summary
- **THEN** report screen time, breaks taken, posture alerts
- **AND** compare to healthy targets

#### Scenario: Pattern detection
- **WHEN** tracking over multiple days
- **THEN** identify concerning patterns
- **AND** suggest improvements

---

### Requirement: Behavior Analysis
The system SHALL analyze user behavior for wellness insights.

#### Scenario: Fatigue detection
- **WHEN** user shows signs of fatigue (yawning, rubbing eyes)
- **THEN** suggest break or early finish
- **AND** log observation

---

## Privacy Considerations
- Camera processing done locally (no cloud)
- No images stored, only derived metrics
- User can disable any monitoring feature

---

## Example Queries
- "How's my posture today?"
- "When did I last take a break?"
- "Show my screen time this week"
