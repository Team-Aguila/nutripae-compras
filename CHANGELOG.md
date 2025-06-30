# Changelog

All notable changes to this project will be documented in this file.


## [Unreleased] - 2025-06-13

### Added
- Implemented detailed menu schedule query (HU#19).
- Enabled citizen consultation of menu cycles and schedules, filterable by campus and town.
- Implemented menu cycle scheduling.

---

## [0.3.0] - 2025-06-12

### Added
- Implemented functionality to create and manage menu cycles.
- Added the capability to assign a menu cycle to a specific campus for a given date range (HU#18).

### Fixed
- Changed the global API prefix to `/api/v1` for versioning.
- Corrected an issue causing duplicate documentation entries for the ingredient service.

---

## [0.2.1] - 2025-06-11

### Fixed
- Resolved two bugs related to the dish filtering functionality (HU#8).

---

## [0.2.0] - 2025-06-11

### Added
- Completed implementation for user story #7.
- Began development on user story #12.

---

## [0.1.0] - 2025-06-11

### Added
- Implemented ingredient filtering, categorization, and statistics.
- Added functionality to activate or inactivate ingredients.
- Created an endpoint to retrieve all active ingredients.
- Completed all user stories related to ingredient management.
- Established initial database models based on the relational schema.

### Changed
- Updated the database connection configuration.
- Changed the method to validate name uniqueness from `GET` to `HEAD` for better efficiency.

### Fixed
- Corrected the ingredient activation endpoint from `.../reactivate` to `.../activate`.
- Fixed various typos in the codebase and documentation.

---

## [Initial] - 2025-06-09

### Added
- A `CODEOWNERS` file was added to the repository to define ownership.
- The initial continuous integration (CI) pipeline was configured.
