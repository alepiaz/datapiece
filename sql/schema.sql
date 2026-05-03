-- =============================================================================
-- STRUCTURAL HIERARCHY
-- Volume -> Chapter -> Page -> Panel
-- =============================================================================

CREATE TABLE Volumes (
    VolumeNumber INT PRIMARY KEY,
    ReleaseDate  DATE
);

CREATE TABLE Sagas (
    SagaID    INTEGER PRIMARY KEY AUTOINCREMENT,
    SagaName  VARCHAR(255) NOT NULL,
    SagaOrder INT NOT NULL
);

CREATE TABLE Arcs (
    ArcID    INTEGER PRIMARY KEY AUTOINCREMENT,
    SagaID   INT NOT NULL,
    ArcName  VARCHAR(255) NOT NULL,
    ArcOrder INT NOT NULL,
    FOREIGN KEY (SagaID) REFERENCES Sagas(SagaID)
);

CREATE TABLE Chapters (
    ChapterID       INT PRIMARY KEY,
    VolumeNumber    INT,
    ArcID           INT,
    ChapterNumber   INT NOT NULL,
    ChapterName     VARCHAR(255),
    PublicationDate DATE,
    PageCount       INT,
    FOREIGN KEY (VolumeNumber) REFERENCES Volumes(VolumeNumber),
    FOREIGN KEY (ArcID)        REFERENCES Arcs(ArcID)
);

CREATE TABLE Locations (
    LocationID   INTEGER PRIMARY KEY AUTOINCREMENT,
    LocationName VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE Pages (
    PageID         INT PRIMARY KEY,
    ChapterID      INT NOT NULL,
    PageNumber     INT NOT NULL,
    IsColorSpread  BOOLEAN DEFAULT FALSE,
    IsDoubleSpread BOOLEAN DEFAULT FALSE,
    IsCoverPage    BOOLEAN DEFAULT FALSE,
    IsCoverStory   BOOLEAN DEFAULT FALSE,
    IsFanRequest   BOOLEAN DEFAULT FALSE,
    IsSbsPage      BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (ChapterID) REFERENCES Chapters(ChapterID)
);

CREATE TABLE Panels (
    PanelID     INT PRIMARY KEY,
    PageID      INT NOT NULL,
    PanelNumber INT NOT NULL,
    IsFlashback BOOLEAN DEFAULT FALSE,
    IsImagined  BOOLEAN DEFAULT FALSE,
    LocationID  INT,
    PanelSize   TEXT CHECK(PanelSize IN ('small', 'medium', 'large', 'full_page')) DEFAULT 'medium',
    FOREIGN KEY (PageID)     REFERENCES Pages(PageID),
    FOREIGN KEY (LocationID) REFERENCES Locations(LocationID)
);

-- =============================================================================
-- CHARACTERS
-- =============================================================================

CREATE TABLE DevilFruits (
    FruitID            INT PRIMARY KEY,
    FruitName          VARCHAR(255) NOT NULL,
    Type               TEXT NOT NULL CHECK(Type IN ('Paramecia', 'Zoan', 'Logia')),
    ZoanSubtype        TEXT CHECK(ZoanSubtype IN ('Regular', 'Ancient', 'Mythical', 'Unknown')),
    IsAwakened         BOOLEAN DEFAULT FALSE,
    IsCanonicallyNamed BOOLEAN DEFAULT TRUE
);

CREATE TABLE Characters (
    CharacterID              INT PRIMARY KEY,
    Name                     VARCHAR(255) NOT NULL,
    Nickname                 VARCHAR(255),
    Gender                   TEXT CHECK(Gender IN ('Male', 'Female', 'Non-Binary', 'Unknown')) DEFAULT 'Unknown',
    Race                     VARCHAR(255) DEFAULT 'Unknown',
    Height                   INT DEFAULT NULL,
    IsMainCharacter          BOOLEAN DEFAULT FALSE,
    IsAlive                  BOOLEAN DEFAULT TRUE,
    DevilFruitID             INT,
    FirstAppearanceChapterID INT,
    FOREIGN KEY (DevilFruitID)             REFERENCES DevilFruits(FruitID),
    FOREIGN KEY (FirstAppearanceChapterID) REFERENCES Chapters(ChapterID)
);

CREATE TABLE Affiliations (
    AffiliationID   INT PRIMARY KEY,
    AffiliationName VARCHAR(255) NOT NULL,
    AffiliationType TEXT CHECK(AffiliationType IN ('Crew', 'Organization', 'Government', 'Criminal', 'Civilian', 'Other')) DEFAULT 'Other'
);

-- Time-ranged affiliation membership anchored to chapters.
-- ToChapterID NULL means the affiliation is currently active.
CREATE TABLE AffiliationHistory (
    HistoryID     INTEGER PRIMARY KEY AUTOINCREMENT,
    CharacterID   INT NOT NULL,
    AffiliationID INT NOT NULL,
    FromChapterID INT,
    ToChapterID   INT,
    FOREIGN KEY (CharacterID)   REFERENCES Characters(CharacterID),
    FOREIGN KEY (AffiliationID) REFERENCES Affiliations(AffiliationID),
    FOREIGN KEY (FromChapterID) REFERENCES Chapters(ChapterID),
    FOREIGN KEY (ToChapterID)   REFERENCES Chapters(ChapterID)
);

CREATE TABLE Abilities (
    AbilityID   INT PRIMARY KEY,
    AbilityName VARCHAR(255) NOT NULL,
    AbilityType TEXT NOT NULL CHECK(AbilityType IN ('Haki', 'DevilFruit', 'FightingStyle', 'Technique', 'Other')),
    HakiType    TEXT CHECK(HakiType IN ('Observation', 'Armament', 'Conquerors', 'None')) DEFAULT 'None'
);

-- =============================================================================
-- APPEARANCES
-- The core analytical table: which character appears in which panel, and how.
-- =============================================================================

CREATE TABLE CharacterAppearances (
    AppearanceID     INT PRIMARY KEY,
    CharacterID      INT NOT NULL,
    PanelID          INT NOT NULL,
    AppearanceType   TEXT CHECK(AppearanceType IN ('Physical', 'Silhouette', 'Portrait', 'Mention')) DEFAULT 'Physical',
    IsSpeaking       BOOLEAN DEFAULT FALSE,
    IsFocusCharacter BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (CharacterID) REFERENCES Characters(CharacterID),
    FOREIGN KEY (PanelID)     REFERENCES Panels(PanelID)
);

-- =============================================================================
-- INTERACTIONS
-- A span of panels in which two or more characters interact.
-- EndPanelID is nullable while the interaction is ongoing.
-- =============================================================================

CREATE TABLE CharacterInteractions (
    InteractionID   INT PRIMARY KEY,
    StartPanelID    INT NOT NULL,
    EndPanelID      INT,
    InteractionType TEXT NOT NULL CHECK(InteractionType IN ('Fight', 'Conversation', 'Alliance', 'Betrayal', 'Rescue', 'Trade', 'Other')),
    Outcome         TEXT CHECK(Outcome IN ('Ongoing', 'Victory', 'Defeat', 'Draw', 'Interrupted', 'Resolved', 'Unknown')) DEFAULT 'Ongoing',
    FOREIGN KEY (StartPanelID) REFERENCES Panels(PanelID),
    FOREIGN KEY (EndPanelID)   REFERENCES Panels(PanelID)
);

CREATE TABLE InteractionCharacters (
    InteractionID INT NOT NULL,
    CharacterID   INT NOT NULL,
    Role          TEXT CHECK(Role IN ('Initiator', 'Recipient', 'Bystander', 'Mediator')) DEFAULT 'Bystander',
    FOREIGN KEY (InteractionID) REFERENCES CharacterInteractions(InteractionID),
    FOREIGN KEY (CharacterID)   REFERENCES Characters(CharacterID)
);

-- =============================================================================
-- RELATIONSHIPS
--
-- Each relationship type has a different temporal model:
--
-- FAMILY      — static biological/adoptive fact, not a narrative event.
--               RevealedAtPanelID: the panel where the reader learns about it.
--               EstablishedChapterID: only for adoptive relationships, the
--               in-universe chapter where the adoption occurred (often in a flashback).
--
-- ROMANTIC    — has a narrative lifecycle: it begins, may be revealed later,
--               and may end.
--               StartPanelID: when the relationship is established in-universe.
--               RevealedAtPanelID: nullable, when the reader first learns of it
--               (only differs from StartPanelID when revealed via flashback).
--               EndPanelID: nullable, when the relationship ends.
--
-- CREWMATE    — the panel-level bond between two specific nakama.
--               Complements AffiliationHistory (which tracks group membership)
--               by capturing the bilateral moment two characters become crewmates.
--               StartPanelID: the iconic panel where they become nakama.
--               RevealedAtPanelID: nullable, if the reader learns about it later.
--               EndPanelID: nullable, if the crewmate bond ends (death, parting).
-- =============================================================================

CREATE TABLE FamilyRelationships (
    RelationshipID      INT PRIMARY KEY,
    Character1ID        INT NOT NULL,
    Character2ID        INT NOT NULL,
    RelationshipType    TEXT NOT NULL CHECK(RelationshipType IN ('Parent', 'Child', 'Sibling')),
    IsAdoptive          BOOLEAN DEFAULT FALSE,
    IsConfirmed         BOOLEAN DEFAULT TRUE,
    RevealedAtPanelID   INT,
    EstablishedChapterID INT,
    FOREIGN KEY (Character1ID)        REFERENCES Characters(CharacterID),
    FOREIGN KEY (Character2ID)        REFERENCES Characters(CharacterID),
    FOREIGN KEY (RevealedAtPanelID)   REFERENCES Panels(PanelID),
    FOREIGN KEY (EstablishedChapterID) REFERENCES Chapters(ChapterID)
);

CREATE TABLE RomanticRelationships (
    RelationshipID     INT PRIMARY KEY,
    Character1ID       INT NOT NULL,
    Character2ID       INT NOT NULL,
    RelationshipStatus TEXT CHECK(RelationshipStatus IN ('Canon', 'Implied', 'Speculative')) DEFAULT 'Speculative',
    StartPanelID       INT,
    RevealedAtPanelID  INT,
    EndPanelID         INT,
    FOREIGN KEY (Character1ID)      REFERENCES Characters(CharacterID),
    FOREIGN KEY (Character2ID)      REFERENCES Characters(CharacterID),
    FOREIGN KEY (StartPanelID)      REFERENCES Panels(PanelID),
    FOREIGN KEY (RevealedAtPanelID) REFERENCES Panels(PanelID),
    FOREIGN KEY (EndPanelID)        REFERENCES Panels(PanelID)
);

CREATE TABLE CrewmateRelationships (
    RelationshipID     INT PRIMARY KEY,
    Character1ID       INT NOT NULL,
    Character2ID       INT NOT NULL,
    AffiliationID      INT NOT NULL,
    StartPanelID       INT NOT NULL,
    RevealedAtPanelID  INT,
    EndPanelID         INT,
    FOREIGN KEY (Character1ID)      REFERENCES Characters(CharacterID),
    FOREIGN KEY (Character2ID)      REFERENCES Characters(CharacterID),
    FOREIGN KEY (AffiliationID)     REFERENCES Affiliations(AffiliationID),
    FOREIGN KEY (StartPanelID)      REFERENCES Panels(PanelID),
    FOREIGN KEY (RevealedAtPanelID) REFERENCES Panels(PanelID),
    FOREIGN KEY (EndPanelID)        REFERENCES Panels(PanelID)
);

-- =============================================================================
-- EVENTS
-- Discrete character state changes anchored to a specific chapter.
-- Modelled as separate tables so each event type has a clean, non-sparse schema.
-- =============================================================================

CREATE TABLE BountyEvents (
    EventID     INTEGER PRIMARY KEY AUTOINCREMENT,
    CharacterID INT NOT NULL,
    ChapterID   INT NOT NULL,
    Bounty      BIGINT NOT NULL,
    FOREIGN KEY (CharacterID) REFERENCES Characters(CharacterID),
    FOREIGN KEY (ChapterID)   REFERENCES Chapters(ChapterID)
);

CREATE TABLE StatusEvents (
    EventID     INTEGER PRIMARY KEY AUTOINCREMENT,
    CharacterID INT NOT NULL,
    ChapterID   INT NOT NULL,
    Status      TEXT NOT NULL CHECK(Status IN ('Alive', 'Injured', 'Dead', 'Unknown', 'Transformed')),
    FOREIGN KEY (CharacterID) REFERENCES Characters(CharacterID),
    FOREIGN KEY (ChapterID)   REFERENCES Chapters(ChapterID)
);

CREATE TABLE FruitAcquisitions (
    EventID     INTEGER PRIMARY KEY AUTOINCREMENT,
    CharacterID INT NOT NULL,
    FruitID     INT NOT NULL,
    ChapterID   INT NOT NULL,
    FOREIGN KEY (CharacterID) REFERENCES Characters(CharacterID),
    FOREIGN KEY (FruitID)     REFERENCES DevilFruits(FruitID),
    FOREIGN KEY (ChapterID)   REFERENCES Chapters(ChapterID)
);
