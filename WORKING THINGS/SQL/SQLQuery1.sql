CREATE TABLE EmployeeSchedule (
    EmployeeName VARCHAR(255),
    EmployeeID VARCHAR(10),
    Date DATE,
    Day VARCHAR(10),
    ScheduledStartTime TIME,
    ScheduledEndTime TIME,
    ActualStartTime TIME,
    ActualEndTime TIME,
    ScheduledWorkingHours DECIMAL(5, 2),
    ActualWorkingHours DECIMAL(5, 2)
);



-- Assuming the table 'EmployeeSchedule' has already been created

-- Insert values for John Doe with EmployeeID JO1234
INSERT INTO EmployeeSchedule VALUES
('John Doe', 'JO1234', '2023-11-13', 'Monday', '09:00', '17:00', '09:05', '17:00', 8.00, 7.55),
('John Doe', 'JO1234', '2023-11-14', 'Tuesday', '09:00', '17:00', '09:00', '17:00', 8.00, 8.00),
('John Doe', 'JO1234', '2023-11-15', 'Wednesday', '09:00', '17:00', '09:10', '16:50', 8.00, 7.83),
('John Doe', 'JO1234', '2023-11-16', 'Thursday', '09:00', '17:00', '09:05', '17:00', 8.00, 7.55),
('John Doe', 'JO1234', '2023-11-17', 'Friday', '09:00', '17:00', '09:00', '16:30', 8.00, 7.5);

-- Insert values for John Doe with EmployeeID 12345
INSERT INTO EmployeeSchedule VALUES
('John Doe', 'JO1234', '2023-11-20', 'Monday', '09:00', '17:00', '08:45', '16:45', 8.00, 8.00),
('John Doe', 'JO1234', '2023-11-21', 'Tuesday', '09:00', '17:00', '08:30', '16:30', 8.00, 8.00),
('John Doe', 'JO1234', '2023-11-22', 'Wednesday', '09:00', '17:00', '08:45', '17:00', 8.00, 8.25),
('John Doe', 'JO1234', '2023-11-23', 'Thursday', '09:00', '17:00', '09:00', '16:45', 8.00, 7.75),
('John Doe', 'JO1234', '2023-11-24', 'Friday', '09:00', '17:00', '08:30', '16:00', 8.00, 7.5);

-- Insert values for Chris Adam with EmployeeID JA1234
INSERT INTO EmployeeSchedule VALUES
('Chris Adam', 'CA1234', '2023-11-13', 'Monday', '09:00', '17:00', '09:10', '16:50', 8.00, 7.83),
('Chris Adam', 'CA1234', '2023-11-14', 'Tuesday', '09:00', '17:00', '09:05', '17:00', 8.00, 7.55),
('Chris Adam', 'CA1234', '2023-11-15', 'Wednesday', '09:00', '17:00', '09:15', '17:00', 8.00, 7.45),
('Chris Adam', 'CA1234', '2023-11-16', 'Thursday', '09:00', '17:00', '09:05', '16:55', 8.00, 7.5),
('Chris Adam', 'CA1234', '2023-11-17', 'Friday', '09:00', '17:00', '09:00', '16:45', 8.00, 7.75);

-- Insert values for Chris Adam with EmployeeID 98765
INSERT INTO EmployeeSchedule VALUES
('Chris Adam', 'CA1234', '2023-11-20', 'Monday', '09:00', '17:00', '08:30', '16:45', 8.00, 8.25),
('Chris Adam', 'CA1234', '2023-11-21', 'Tuesday', '09:00', '17:00', '08:45', '16:30', 8.00, 7.75),
('Chris Adam', 'CA1234', '2023-11-22', 'Wednesday', '09:00', '17:00', '09:00', '16:15', 8.00, 7.25),
('Chris Adam', 'CA1234', '2023-11-23', 'Thursday', '09:00', '17:00', '08:30', '16:00', 8.00, 7.5),
('Chris Adam', 'CA1234', '2023-11-24', 'Friday', '09:00', '17:00', '09:00', '16:30', 8.00, 7.5);


-- Insert values for Thomas with EmployeeID MS1234
INSERT INTO EmployeeSchedule VALUES
('Thomas', 'TS1234', '2023-11-13', 'Monday', '09:00', '17:00', '09:08', '16:58', 8.00, 7.8),
('Thomas', 'TS1234', '2023-11-14', 'Tuesday', '09:00', '17:00', '09:03', '17:02', 8.00, 7.97),
('Thomas', 'TS1234', '2023-11-15', 'Wednesday', '09:00', '17:00', '09:12', '16:55', 8.00, 7.72),
('Thomas', 'TS1234', '2023-11-16', 'Thursday', '09:00', '17:00', '09:07', '16:53', 8.00, 7.77),
('Thomas', 'TS1234', '2023-11-17', 'Friday', '09:00', '17:00', '09:05', '16:47', 8.00, 7.75);

-- Insert values for Thomas with EmployeeID 54321
INSERT INTO EmployeeSchedule VALUES
('Thomas', 'TS1234', '2023-11-20', 'Monday', '09:00', '17:00', '08:45', '17:00', 8.00, 8.25),
('Thomas', 'TS1234', '2023-11-21', 'Tuesday', '09:00', '17:00', '09:00', '16:30', 8.00, 7.5),
('Thomas', 'TS1234', '2023-11-22', 'Wednesday', '09:00', '17:00', '08:30', '16:45', 8.00, 8.25),
('Thomas', 'TS1234', '2023-11-23', 'Thursday', '09:00', '17:00', '08:45', '16:00', 8.00, 7.25),
('Thomas', 'TS1234', '2023-11-24', 'Friday', '09:00', '17:00', '09:00', '16:15', 8.00, 7.25);


-- Insert values for Peter Jones with EmployeeID PJ1234
INSERT INTO EmployeeSchedule VALUES
('Peter Jones', 'PJ1234', '2023-11-13', 'Monday', '09:00', '17:00', '09:05', '17:05', 8.00, 7.5),
('Peter Jones', 'PJ1234', '2023-11-14', 'Tuesday', '09:00', '17:00', '08:55', '17:10', 8.00, 7.25),
('Peter Jones', 'PJ1234', '2023-11-15', 'Wednesday', '09:00', '17:00', '09:10', '16:50', 8.00, 7.67),
('Peter Jones', 'PJ1234', '2023-11-16', 'Thursday', '09:00', '17:00', '08:55', '17:05', 8.00, 7.5),
('Peter Jones', 'PJ1234', '2023-11-17', 'Friday', '09:00', '17:00', '09:00', '16:50', 8.00, 7.83);

-- Insert values for Peter Jones with EmployeeID 12345
INSERT INTO EmployeeSchedule VALUES
('Peter Jones', 'PJ1234', '2023-11-20', 'Monday', '09:00', '17:00', '08:45', '16:30', 8.00, 7.75),
('Peter Jones', 'PJ1234', '2023-11-21', 'Tuesday', '09:00', '17:00', '08:30', '16:45', 8.00, 8.25),
('Peter Jones', 'PJ1234', '2023-11-22', 'Wednesday', '09:00', '17:00', '09:00', '16:15', 8.00, 7.25),
('Peter Jones', 'PJ1234', '2023-11-23', 'Thursday', '09:00', '17:00', '08:45', '16:00', 8.00, 7.5),
('Peter Jones', 'PJ1234', '2023-11-24', 'Friday', '09:00', '17:00', '09:00', '16:30', 8.00, 7.5);


-- Create table
CREATE TABLE EmployeeLeave (
    EmployeeName VARCHAR(255),
    EmployeeID VARCHAR(10),
    SickLeave INT,
    PrivilegeLeave INT,
    PaternityLeave INT,
    UpcomingThreeLeaves VARCHAR(100),
    Year INT
);

-- Insert values
INSERT INTO EmployeeLeave VALUES
('John Doe', 'JO1234', 3, 10, 15, '2023-12-25,2023-12-26,2023-12-27', 2023),
('Chris Adam', 'JA1234', 4, 10, 0, '2023-12-26,2023-12-27,2023-12-28', 2023),
('Peter Jones', 'PJ1234', 3, 10, 15, '2023-12-29,2023-12-30,2023-12-31', 2023),
('Thomas', 'MS1234', 4, 10, 0, '2023-12-20,2023-12-21,2023-12-22', 2023);

select * from EmployeeLeave;
select * from  EmployeeSchedule;


