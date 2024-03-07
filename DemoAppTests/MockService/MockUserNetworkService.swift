//
//  MockUserNetworkService.swift
//  DemoAppTests
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation
import Combine
import NBNetworking
@testable import DemoApp

class MockUserNetworkService: UserNetworkService {

    static let shared = MockUserNetworkService()
    var userModelList: [UserModel]?
    var getUsereCount: Int = 0

    func getUserData(url: String) -> AnyPublisher<[UserModel], NBURLSessionError> {
        if let result = userModelList {
            let model = UserModel.previewUserModel()
            userModelList = [model]
            getUsereCount = result.count
            return Just(result)
                .setFailureType(to: NBURLSessionError.self)
                .eraseToAnyPublisher()
        }
        return Fail(error: NBURLSessionError.responseError)
            .eraseToAnyPublisher()
    }
}
