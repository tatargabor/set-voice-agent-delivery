## ADDED Requirements

### Requirement: Lookup caller from contacts file
The system SHALL map incoming phone numbers to customer data using a `contacts.yaml` file.

#### Scenario: Known phone number
- **WHEN** caller phone matches an entry in `contacts.yaml`
- **THEN** the system SHALL return the customer_name, company_name, script, and optional fields

#### Scenario: Unknown phone number
- **WHEN** caller phone is not in `contacts.yaml`
- **THEN** the system SHALL return the default context from the `default` section

### Requirement: Contacts file format
The contacts file SHALL be a YAML file with phone numbers as keys mapping to customer data.

#### Scenario: Valid contacts file
- **WHEN** `contacts.yaml` contains entries with phone numbers and customer data
- **THEN** each entry SHALL have at minimum: customer_name, company_name, script

### Requirement: Hot reload contacts
The system SHALL reload `contacts.yaml` on each incoming call so new contacts can be added without restarting the server.

#### Scenario: Contact added while server running
- **WHEN** a new contact is added to `contacts.yaml` while the server is running
- **THEN** the next incoming call from that number SHALL use the new contact data
