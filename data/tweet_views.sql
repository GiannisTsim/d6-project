-- Tweet Views

DROP VIEW IF EXISTS Tweet_Text_V;
CREATE VIEW Tweet_Text_V
AS 
SELECT  Tweet_Complete.TweetId,
        AuthorId,
        TweetDtm,
        Lang,
        Tweet
FROM Tweet_Complete
INNER JOIN Tweet_Text
ON Tweet_Complete.TweetId = Tweet_Text.TweetId;


-- Edge views

-- A retweets B
DROP VIEW IF EXISTS EdgeRetweet_V;
CREATE VIEW EdgeRetweet_V           
AS
SELECT DISTINCT RT.AuthorId AS A,
                T.AuthorId  AS B
FROM Tweet_Retweet
INNER JOIN Tweet_Complete   AS RT
ON RetweetId = RT.TweetId
INNER JOIN Tweet_Complete   AS T
ON ReferenceTweetId = T.TweetId
WHERE RT.AuthorId != T.AuthorId;

DROP VIEW IF EXISTS EdgeWeightedRetweet_V;
CREATE VIEW EdgeWeightedRetweet_V           
AS
SELECT  RT.AuthorId AS A,
        T.AuthorId  AS B,
        COUNT(*)    AS Weight
FROM Tweet_Retweet
INNER JOIN Tweet_Complete   AS RT
ON RetweetId = RT.TweetId
INNER JOIN Tweet_Complete   AS T
ON ReferenceTweetId = T.TweetId
WHERE RT.AuthorId != T.AuthorId
GROUP BY RT.AuthorId, T.AuthorId;

-- A quotes B
DROP VIEW IF EXISTS EdgeQuote_V;
CREATE VIEW EdgeQuote_V           
AS
SELECT DISTINCT QT.AuthorId AS A,
                T.AuthorId  AS B
FROM TweetReference         AS RF
INNER JOIN Tweet_Complete   AS QT
ON RF.TweetId = QT.TweetId
INNER JOIN Tweet_Complete   AS T
ON RF.ReferenceTweetId = T.TweetId
WHERE RF.ReferenceTypeCode = 'Qu'
AND QT.AuthorId != T.AuthorId;

DROP VIEW IF EXISTS EdgeWeightedQuote_V;
CREATE VIEW EdgeWeightedQuote_V           
AS
SELECT  QT.AuthorId AS A,
        T.AuthorId  AS B,
        COUNT(*)    AS Weight
FROM TweetReference         AS RF
INNER JOIN Tweet_Complete   AS QT
ON RF.TweetId = QT.TweetId
INNER JOIN Tweet_Complete   AS T
ON RF.ReferenceTweetId = T.TweetId
WHERE RF.ReferenceTypeCode = 'Qu'
AND QT.AuthorId != T.AuthorId
GROUP BY QT.AuthorId, T.AuthorId;

-- A replies to B
DROP VIEW IF EXISTS EdgeReply_V;
CREATE VIEW EdgeReply_V           
AS
SELECT DISTINCT RE.AuthorId AS A,
                T.AuthorId  AS B
FROM TweetReference         AS RF
INNER JOIN Tweet_Complete   AS RE
ON RF.TweetId = RE.TweetId
INNER JOIN Tweet_Complete   AS T
ON RF.ReferenceTweetId = T.TweetId
WHERE RF.ReferenceTypeCode = 'Re'
AND RE.AuthorId != T.AuthorId;

DROP VIEW IF EXISTS EdgeWeightedReply_V;
CREATE VIEW EdgeWeightedReply_V           
AS
SELECT  RE.AuthorId AS A,
        T.AuthorId  AS B,
        COUNT(*)    AS Weight
FROM TweetReference         AS RF
INNER JOIN Tweet_Complete   AS RE
ON RF.TweetId = RE.TweetId
INNER JOIN Tweet_Complete   AS T
ON RF.ReferenceTweetId = T.TweetId
WHERE RF.ReferenceTypeCode = 'Re'
AND RE.AuthorId != T.AuthorId
GROUP BY RE.AuthorId, T.AuthorId;

-- A mentions B
DROP VIEW IF EXISTS EdgeMention_V;
CREATE VIEW EdgeMention_V           
AS
SELECT DISTINCT AuthorId            AS A,
                MentionAccountId    AS B
FROM Tweet_Complete         AS T
INNER JOIN Entity_Mention   AS M
ON T.TweetId = M.TweetId
WHERE AuthorId != MentionAccountId;

DROP VIEW IF EXISTS EdgeWeightedMention_V;
CREATE VIEW EdgeWeightedMention_V           
AS
SELECT  AuthorId            AS A,
        MentionAccountId    AS B,
        COUNT(*)            AS Weight
FROM Tweet_Complete         AS T
INNER JOIN Entity_Mention   AS M
ON T.TweetId = M.TweetId
WHERE AuthorId != MentionAccountId
GROUP BY AuthorId, MentionAccountId;

