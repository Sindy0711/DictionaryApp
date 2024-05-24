CREATE TABLE NguoiDung (
    id_user SERIAL PRIMARY KEY,
    ten_dang_nhap VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    mat_khau VARCHAR(255) NOT NULL,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE BaiHoc (
    id_baihoc SERIAL PRIMARY KEY,
    tieu_de VARCHAR(255) NOT NULL,
    mo_ta TEXT NOT NULL,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TuVung (
    ma_tu_vung SERIAL PRIMARY KEY,
    tu VARCHAR(255) NOT NULL,
    phienam VARCHAR(255),
    nghia TEXT NOT NULL,
    vi_du TEXT,
    ma_bai_hoc INT, FOREIGN KEY (ma_bai_hoc) REFERENCES BaiHoc(id_baihoc)
);

CREATE TABLE NguPhap (
    ma_ngu_phap SERIAL PRIMARY KEY,
    tieu_de VARCHAR(255) NOT NULL,
    mo_ta TEXT NOT NULL,
    ma_bai_hoc INT,
    FOREIGN KEY (ma_bai_hoc) REFERENCES BaiHoc(id_baihoc)
);

CREATE TABLE BaiKiemTra (
    ma_bai_kiem_tra SERIAL PRIMARY KEY,
    tieu_de VARCHAR(255) NOT NULL,
    ma_bai_hoc INT,
    FOREIGN KEY (ma_bai_hoc) REFERENCES BaiHoc(id_baihoc)
);

CREATE TABLE KetQuaKiemTra (
    ma_ket_qua SERIAL PRIMARY KEY,
    ma_nguoi_dung INT,
    ma_bai_kiem_tra INT,
    diem INT NOT NULL,
    ngay_thi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(id_user),
    FOREIGN KEY (ma_bai_kiem_tra) REFERENCES BaiKiemTra(ma_bai_kiem_tra)
);