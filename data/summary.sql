DELETE FROM TweetCountSummary;
INSERT INTO TweetCountSummary (AuthorId, Lang, Count)
SELECT  AuthorId, 
        Lang, 
        COUNT(*) AS Count
FROM Tweet_Complete
INNER JOIN Tweet_Text
ON Tweet_Complete.TweetId = Tweet_Text.TweetId
GROUP BY AuthorId, Lang;