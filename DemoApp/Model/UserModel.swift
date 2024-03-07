//
//  UserModel.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation

struct UserModel: Codable, Identifiable, Equatable {
    let id: Int
    let name: String
    var company: CompanyModel?

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(Int.self, forKey: .id)
        self.name = try container.decode(String.self, forKey: .name)
        self.company = try container.decodeIfPresent(CompanyModel.self, forKey: .company)
    }

    init(id: Int, name: String, company: CompanyModel) {
        self.id = id
        self.name = name
        self.company = company
    }

    static func previewUserModel() -> UserModel {
       return UserModel(
           id: 1,
           name: "Navnit",
           company: CompanyModel(name: "Thoughtworks")
       )
   }
}
