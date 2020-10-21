# -*- coding: utf-8 -*-

# Add table Migrations
# Set initial database_version

steps = [
    """
CREATE TABLE IF NOT EXISTS Migrations(
    database_version INT)
""",
    """
INSERT INTO Migrations (database_version) VALUES (1)
""",
]

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79
