-- Account Cluster -----------------------------------------------------------

CREATE TABLE Account(
    AccountId   TEXT NOT NULL,
    Username    TEXT NOT NULL,
    PRIMARY KEY (AccountId),
    UNIQUE (Username)
);

-- Tweet Cluster -------------------------------------------------------------

CREATE TABLE TweetType(
    TweetTypeCode   TEXT    NOT NULL,
    TweetType       TEXT    NOT NULL,
    PRIMARY KEY (TweetTypeCode),
    UNIQUE (TweetType)
);
INSERT INTO TweetType VALUES ('U', 'Unavailable'), ('P', 'Partial'), ('C', 'Complete');

CREATE TABLE ReferenceType(
    ReferenceTypeCode   TEXT    NOT NULL,
    ReferenceType       TEXT    NOT NULL,
    PRIMARY KEY (ReferenceTypeCode),
    UNIQUE (ReferenceType)
);
INSERT INTO ReferenceType VALUES ('Qu', 'Quote'), ('Re', 'Reply');

CREATE TABLE Tweet(
    TweetId         TEXT    NOT NULL,
    TweetTypeCode   TEXT    NOT NULL,
    PRIMARY KEY (TweetId),
    FOREIGN KEY (TweetTypeCode) REFERENCES TweetType (TweetTypeCode)
);

CREATE TABLE Tweet_Unavailable(
    TweetId     TEXT    NOT NULL,
    PRIMARY KEY (TweetId),
    FOREIGN KEY (TweetId) REFERENCES Tweet (TweetId)
);

CREATE TABLE Tweet_Partial(
    TweetId     TEXT    NOT NULL,
    PRIMARY KEY (TweetId),
    FOREIGN KEY (TweetId) REFERENCES Tweet (TweetId)
);

CREATE TABLE Tweet_Complete(
    TweetId     TEXT    NOT NULL,
    AuthorId    TEXT    NOT NULL,
    TweetDtm    TEXT    NOT NULL,
    IsRetweet   BOOLEAN NOT NULL,
    PRIMARY KEY (TweetId),
    FOREIGN KEY (TweetId) REFERENCES Tweet (TweetId),
    FOREIGN KEY (AuthorId) REFERENCES Account (AccountId)
);

CREATE TABLE Tweet_Text(
    TweetId TEXT    NOT NULL,
    Tweet   TEXT    NOT NULL,
    Lang    TEXT    NOT NULL,
    PRIMARY KEY (TweetId),
    FOREIGN KEY (TweetId) REFERENCES Tweet_Complete (TweetId)
);

CREATE TABLE Tweet_Retweet(
    RetweetId           TEXT    NOT NULL,
    ReferenceTweetId    TEXT    NOT NULL,
    PRIMARY KEY (RetweetId),
    FOREIGN KEY (RetweetId) REFERENCES Tweet_Complete (TweetId),
    FOREIGN KEY (ReferenceTweetId) REFERENCES Tweet_Text (TweetId)
);

CREATE TABLE TweetReference(
    TweetId             TEXT    NOT NULL,
    ReferenceTypeCode   TEXT    NOT NULL,
    ReferenceTweetId    TEXT    NOT NULL,
    PRIMARY KEY (TweetId, ReferenceTypeCode),
    FOREIGN KEY (TweetId) REFERENCES Tweet_Text (TweetId),
    FOREIGN KEY (ReferenceTypeCode) REFERENCES ReferenceType (ReferenceTypeCode),
    FOREIGN KEY (ReferenceTweetId) REFERENCES Tweet (TweetId)
);

-- Entity Cluster -------------------------------------------------------------

CREATE TABLE EntityType(
    EntityTypeCode  TEXT    NOT NULL,
    EntityType      TEXT    NOT NULL,
    PRIMARY KEY (EntityTypeCode),
    UNIQUE (EntityType)
);
INSERT INTO EntityType VALUES ('An', 'Annotation'), ('Ha', 'Hashtag'), ('Me', 'Mention'), ('Ur', 'Url');

CREATE TABLE AnnotationType(
    AnnotationTypeCode  TEXT    NOT NULL,
    AnnotationType      TEXT    NOT NULL,
    PRIMARY KEY (AnnotationTypeCode),
    UNIQUE (AnnotationType)
);
INSERT INTO AnnotationType VALUES ('Pe', 'Person'), ('Pl', 'Place'), ('Pr', 'Product'), ('Or', 'Organization'), ('O', 'Other');

CREATE TABLE Hashtag(
    Hashtag TEXT    NOT NULL,
    PRIMARY KEY (Hashtag)
);

CREATE TABLE Annotation(
    AnnotationTypeCode  TEXT    NOT NULL,
    Annotation          TEXT    NOT NULL,
    PRIMARY KEY (AnnotationTypeCode, Annotation),
    FOREIGN KEY (AnnotationTypeCode) REFERENCES AnnotationType (AnnotationTypeCode)
);

CREATE TABLE Entity(
    TweetId         TEXT    NOT NULL,
    EntityNo        INTEGER NOT NULL,
    EntityTypeCode  TEXT    NOT NULL,
    OffsetStart     INTEGER NOT NULL,
    OffsetEnd       INTEGER NOT NULL,
    PRIMARY KEY (TweetId, EntityNo),
    FOREIGN KEY (TweetId) REFERENCES Tweet_Text (TweetId),
    FOREIGN KEY (EntityTypeCode) REFERENCES EntityType (EntityTypeCode)
);

CREATE TABLE Entity_Mention(
    TweetId             TEXT    NOT NULL,
    EntityNo            INTEGER NOT NULL,
    MentionAccountId    TEXT    NOT NULL,
    PRIMARY KEY (TweetId, EntityNo),
    FOREIGN KEY (TweetId, EntityNo) REFERENCES Entity (TweetId, EntityNo),
    FOREIGN KEY (MentionAccountId) REFERENCES Account (AccountId)
);

CREATE TABLE Entity_Hashtag(
    TweetId     TEXT    NOT NULL,
    EntityNo    INTEGER NOT NULL,
    Hashtag     TEXT    NOT NULL,
    PRIMARY KEY (TweetId, EntityNo),
    FOREIGN KEY (TweetId, EntityNo) REFERENCES Entity (TweetId, EntityNo),
    FOREIGN KEY (Hashtag) REFERENCES Hashtag (Hashtag)
);

CREATE TABLE Entity_Annotation(
    TweetId             TEXT    NOT NULL,
    EntityNo            INTEGER NOT NULL,
    AnnotationTypeCode  TEXT    NOT NULL,
    Annotation          TEXT    NOT NULL,
    PRIMARY KEY (TweetId, EntityNo),
    FOREIGN KEY (TweetId, EntityNo) REFERENCES Entity (TweetId, EntityNo),
    FOREIGN KEY (AnnotationTypeCode, Annotation) REFERENCES Annotation (AnnotationTypeCode, Annotation)
);

CREATE TABLE Entity_Url(
    TweetId     TEXT    NOT NULL,
    EntityNo    INTEGER NOT NULL,
    Url         TEXT    NOT NULL,
    PRIMARY KEY (TweetId, EntityNo),
    FOREIGN KEY (TweetId, EntityNo) REFERENCES Entity (TweetId, EntityNo)
);


-- Summary Cluster -------------------------------------------------------------

CREATE TABLE TweetCountSummary(
    AuthorId    TEXT    NOT NULL,
    Lang        TEXT    NOT NULL,
    Count       INTEGER NOT NULL,
    PRIMARY KEY (AuthorId, Lang),
    FOREIGN KEY (AuthorId) REFERENCES Account (AccountId)
);