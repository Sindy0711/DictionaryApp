-- Bảng Users
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng Vocabulary
CREATE TABLE Vocabulary (
    word_id SERIAL PRIMARY KEY,
    word VARCHAR(255) NOT NULL,
    pronunciation VARCHAR,
    meaning TEXT NOT NULL,
    description TEXT,
    example TEXT
);
-- Bảng VocabularyPage
CREATE TABLE VocabularyPage (
    page_id SERIAL PRIMARY KEY,
    page_name VARCHAR(255),
    icon TEXT,
    description TEXT,
    user_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Bảng CauHoi
CREATE TABLE Questions (
    question_id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT NOT NULL,
    choice_d TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    page_id INT,
    FOREIGN KEY (page_id) REFERENCES VocabularyPage(page_id)
);

-- Bảng LearningProgress
CREATE TABLE LearningProgress (
    page_id INT,
    user_id INT,
    word_id INT,
    score INT NOT NULL,
    study_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_study_date TIMESTAMP,
    PRIMARY KEY (page_id, user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (word_id) REFERENCES Vocabulary(word_id),
    FOREIGN KEY (page_id) REFERENCES VocabularyPage(page_id)
);
