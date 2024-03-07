//
//  CompanyModel.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation

struct CompanyModel: Codable, Equatable {
    var name: String

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.name = try container.decode(String.self, forKey: .name)
    }

     init(name: String) {
        self.name = name
    }

    static func previewCompanyModel() -> CompanyModel {
       return CompanyModel(
        name: "Thoughtworks"
       )
   }
}
