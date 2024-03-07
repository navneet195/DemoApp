//
//  Constants.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation

struct APIEndPoints {
    static let baseURL = "https://jsonplaceholder.typicode.com/"
    static let user = "users"
}

enum Constants {
    static let name = "Name:"
    static let companyName = "Company name:"
    static let userDetail = "User detail"
    static let userList = "User List"
 }


struct DetailViewConstants {
    static let currentCompanyName = "Current Company Name:"
    static let enterComapnyName = "Enter comapny name"
    static let doneButton = "Done"
}


enum ErrorMessage {
    static let serverErrorMessage = "Sorry, the connection to our server failed."
 }
