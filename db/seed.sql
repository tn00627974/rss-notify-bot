INSERT INTO platform (name)
VALUES 
('discord'),
('line');

INSERT INTO rss_source (rss_url, display_name)
VALUES
('https://tw.stock.yahoo.com/rss?category=tw-market', '台股市場'),
('https://tw.stock.yahoo.com/rss?category=personal-finance', '個人理財'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UCPIDQXQBGyBKj7fAuJIk-ag', 'PFY玩給你看'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UCVXaorXfGwSGBBoyr00dAhg', '一發入魂'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UCF3X_V1Gd5yagyTgwIIScag', '平民百姓'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UCSHzAI3rwHtHN9XS9mRkWGw', 'Rod / 隨便玩'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UCpmszDgk135POU3WxpdVt1g', '阿瑞斯Ares'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UC_IaXjkXABqXjLjiIHDJPqw', '微笑'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UC_XZ4O10pZq9RCigggGSB1A', 'CD喜德'),
('https://www.youtube.com/feeds/videos.xml?channel_id=UCjCSgRei43lOxiTwpQakXVg', '三叔公'),
('https://www.ithome.com.tw/rss', 'IThome新聞');

INSERT INTO target (platform_id, external_id, mention_user_id, description) 
VALUES
(1, '1471437966114291795', '401030097093525514', 'Dc:台股動態', NULL),
(1, '1478028289862930576', '401030097093525514', 'Dc:小資理財', NULL),
(1, '1479863790156648590', NULL, 'Dc:RO世界-Yt影片'),
(1, '1507638723997860031', '401030097093525514', 'Dc:資訊日報', NULL)

INSERT INTO target (platform_id, external_id, mention_user_id, description)
VALUES
(2, 'Ca3e813c39a0091749eaac4c6c63641e8', NULL, 'Group:阿母股票'),
(2, 'Cc36965bdf5691eb6e774add9ba663513', NULL, 'Group:Youtube 通知快訊');

INSERT INTO rss_source_target (rss_source_id, target_id)
VALUES
-- 台股市場
(1, 1),
(1, 4),

-- 個人理財
(2, 2),
(2, 4),

-- PFY
(3, 3),
(3, 5),

-- 一發入魂
(4, 3),
(4, 5),

-- 平民百姓
(5, 3),
(5, 5),

-- Rod
(6, 3),
(6, 5),

-- 阿瑞斯
(7, 3),
(7, 5),

-- 微笑
(8, 3),
(8, 5),

-- CD喜德
(9, 3),
(9, 5),

-- 三叔公
(10, 3),
(10, 5),

-- 資訊日報
(11, 6);