-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create chat_sessions table
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create chat_messages table
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    content TEXT,
    role TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

-- Add indexes to improve query performance
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);

-- Add unique constraint to prevent duplicate emails
ALTER TABLE users ADD CONSTRAINT unique_email UNIQUE (email);



-- Create appointments table
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    doctor_id TEXT, -- Corresponds to the 'id' in your JSON file (e.g., 'H-001')
    doctor_name TEXT,
    hospital_name TEXT,
    patient_name TEXT,
    patient_email TEXT,
    patient_phone TEXT,
    preferred_city TEXT,
    preferred_day TEXT,
    status TEXT DEFAULT 'Pending', -- e.g., 'Pending', 'Confirmed'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Add an index for faster lookups by user
CREATE INDEX idx_appointments_user_id ON appointments(user_id);