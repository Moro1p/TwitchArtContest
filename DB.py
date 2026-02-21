import sqlite3

class DataBaseManager:
    def __init__(self):
        self.db = sqlite3.connect("./database/Authors")
        self.cursor = self.db.cursor()
        self.total_scores = 0
        self._init_records()
        self.current_id = None
        self.total_authors = len(self.authors)
        if self.authors:
            self.current_id = self.authors[0]["id"]

    def _init_records(self):
        self.total_scores = 0
        self.authors = []
        self.cursor.execute("SELECT * FROM authors")
        for row in self.cursor.fetchall():
            elem = dict()
            elem["id"] = row[0]-1
            elem["nickname"] = row[1]
            elem["link_social_media"] = row[2]
            elem["art_path"] = row[3]
            elem["score"] = None
            elem["comment"] = row[5]
            if row[4]:
                self.total_scores += 1
                elem["score"] = str(row[4])
            self.authors.append(elem)
    
    def AddAuthor(self, nickname, social_media_link, path_to_image):
        try:
            self.cursor.execute(
                "INSERT INTO authors (name, social_media_link, art_path) VALUES (?, ?, ?)", 
                (nickname, social_media_link, path_to_image)
            )
            
            self.db.commit()
            
            print(f"Автор '{nickname}' успешно добавлен. ID: {self.cursor.lastrowid}")
            
            if self.current_record is None:
                self._init_records()
                
            return True
            
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении автора: {e}")
            self.db.rollback()
            return False
    
    def UpdateScore(self, author_id, score):
        try:
            self.cursor.execute(
                "UPDATE authors SET score = ? WHERE id = ?", (score, author_id)
            )
            self.db.commit()
            print(f"Оценка'{author_id}' успешно обновлена.")
            return True
        
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении оценки: {e}")
            self.db.rollback()
            return False

    def get_all_authors(self):
        self.cursor.execute("SELECT * FROM authors ORDER BY id")
        return self.cursor.fetchall()
    
    def close(self):
        self.db.close()
